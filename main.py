from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
import sys
import re
from dotenv import load_dotenv
import json 
import logging
from typing import List
from jsonschema import validate, ValidationError
import requests
import pandas as pd
from io import StringIO

#set up logging
logging.basicConfig(level=logging.INFO) 

#Load environment varaibles from .env file
load_dotenv()

app = FastAPI()

#Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #"https://momokaiwase.github.io" when deployed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Load OpenAI API key from environment variable
client = OpenAI(
    #This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)

VEGA_LITE_SCHEMA_URL = "https://vega.github.io/schema/vega-lite/v5.json"

class ColumnInfo(BaseModel):
    name: str
    type: str

class QueryRequest(BaseModel):
    prompt: str
    sample_data: str

class QueryResponse(BaseModel):
    response: str
    vegaSpec: dict

class CodeResponse(BaseModel):
    code: str

generate_chart = {
    "type": "function",
    "function" : {
        "name": "generate_chart",
        "description": "Generate a chart based on the question and data.",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "The data to generate the Vega-Lite JSON specification for.",
                },
                "input_prompt": {
                    "type": "string",
                    "description":"The prompt to generate the Vega-Lite JSON specification based on.",
                },
            },
        },
        "required": ["data", "input_prompt"],
        "additionalProperties": False,
    },
}

data_analysis_code = {
    "type": "function",
    "function" : {
        "name": "data_analysis_code",
        "description": "Generate python code to perform the given data analysis task.",
        "parameters": {
            "type": "object",
            "properties": {
                "data" : {
                    "type" : "string",
                    "description" : "The data to use in the python code.",
                },
                "task": {
                    "type": "string",
                    "description": "The task to generate python code for.",
                },
            },
        },
        "required": ["data", "task"],
        "additionalProperties": False,
    },
}

execute_panda_dataframe_code = {
    "type" : "function",
    "function" : {
        "name" : "execute_panda_dataframe_code",
        "description" : "Executes the given code.",
        "parameters" : {
            "type" : "object",
            "properties" : {
                "code" : {
                    "type" : "string",
                    "description" : "The python code to execute."
                }
            },
            "required" : ["code"],
            "additionalProperties": False
        }
    }
}


tools = [generate_chart, data_analysis_code, execute_panda_dataframe_code]

def validate_vega_lite_spec(spec: dict):
    try:
        schema = requests.get(VEGA_LITE_SCHEMA_URL).json()
        validate(instance=spec, schema=schema)
        return True
    except ValidationError as e:
        logging.error(f"Vega-Lite spec validation error: {str(e)}")
        return False
    

def generate_chart(data, input_prompt):
    print("entered generate_chart")
    system_prompt = f"""
        You are an AI assistant designed to generate vega-lite specifications. Make sure that the response adheres to this example general format: {{
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {{
             "values": [
            {{"category":"A", "group": "x", "value":0.1}},
            {{"category":"C", "group": "y", "value":0.6}},
            {{"category":"A", "group": "z", "value":0.9}},
            {{"category":"B", "group": "x", "value":0.7}},
            ]
            }},
        "mark": "bar",
        "encoding": {{
            "x": {{"field": "category"}},
            "y": {{"field": "value", "type": "quantitative"}},
            "xOffset": {{"field": "group"}},
            "color": {{"field": "group"}}
            }}
        }}
        Include the schema, the data, mark, and encoding fields. Encoding should include the correct fields and types.
        If there is an issue generating the visualization, please return an empty vega-lite JSON specification.
        Your response must be a vega-lite JSON specification with one data point, and a description.
        """
    
    vega_lite_prompt = f"""
        Generate a JSON object with two fields:
        1. "vegaSpec": A valid Vega-Lite JSON specification with data from {data} based on the prompt: {input_prompt}
        2. "response": A brief textual description explaining the graph.
        Make sure that the response is a properly formatted JSON object.
    """
    
    # Call the OpenAI API via LangChain
    try:
        chat_completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": vega_lite_prompt}
            ],
        )
        logging.info(f"OpenAI API response: {chat_completion}")
    except Exception as e:
        logging.error(f"API call failed: {e}")
        raise HTTPException(status_code=500, detail="API call failed.")

    ai_response = chat_completion.choices[0].message.content
    logging.info(f"Received response from generate_chart: {ai_response}")  # Log AI response
    
    try:
        ai_response_json = json.loads(ai_response)
    except json.JSONDecodeError as e:
        return QueryResponse(response="There was an issue generating the visualization, please try again.", vegaSpec={})
    
    vega_spec = ai_response_json.get("vegaSpec", {})
    #logging.info(f"Received vegaSpec from generate_chart: {vega_spec}")
    text_response = ai_response_json.get("response", {})
    #logging.info(f"Received vegaSpec from generate_chart: {text_response}")

    if not validate_vega_lite_spec(vega_spec):
        return QueryResponse(
        response="This task doesn't require chart generation. Returning an empty Vega-Lite specification.",
        vegaSpec={},
        )

    return QueryResponse(response=text_response, vegaSpec = vega_spec)

def sanitize_input(query: str) -> str:
    """Sanitize input to the python REPL.
        Remove whitespace, backtick & python (if llm mistakes python console as terminal
    """
    # Removes `, whitespace & python from start
    query = re.sub(r"^(\s|`)*(?i:python)?\s*", "", query)
    # Removes whitespace & ` from end
    query = re.sub(r"(\s|`)*$", "", query)
    return query

def execute_panda_dataframe_code(code):
    """
    Execute the given python code and return the output. 
    References:
    1. https://github.com/langchain-ai/langchain-experimental/blob/main/libs/experimental/langchain_experimental/utilities/python.py
    2. https://github.com/langchain-ai/langchain-experimental/blob/main/libs/experimental/langchain_experimental/tools/python/tool.py
    """
    # Save the current standard output to restore later
    old_stdout = sys.stdout
    # Redirect standard output to a StringIO object to capture any output generated by the code execution
    sys.stdout = mystdout = StringIO()
    try:
        # Execute the provided code within the current environment
        cleaned_command = sanitize_input(code)
        exec(cleaned_command)
                
        # Restore the original standard output after code execution
        sys.stdout = old_stdout
                        
        # Return any captured output from the executed code
        return mystdout.getvalue()
    except Exception as e:
        sys.stdout = old_stdout
        return repr(e)

def data_analysis_code(data, task):
    print("entered data_analysis_code function")
    code_prompt = f"Generate python code to perform the following task: {task} using the data {data}. Print the result using python print(result). The python code should only be used for calculations presented by text instead of data visualizations."
    system_prompt = f"""You are an AI assistant who is an expert in producing code.
        Output python code that can solve the task from the input prompt, taking the following steps.
        1. Collect needed information. Produce code that will output the information needed to perform the task. After sufficient information is printed, the task can be solved based off of mathematics and language skills.
        2. Perform a task with code, using python code to efficiently perform the task and output the result.
        For example, the output for the input prompt "compute the median miles per gallon (mpg) of European cars from the 'cars' dataset" might look like the following
        code = 
            'european_cars = cars[cars['origin'] == 'Europe']
            median_mpg = european_cars['mpg'].median()
            print(median_mpg)'
        The result returned should be code without explanations. It should be complete code that the user can then execute without adding or changing anything. Do not generate code that creates visualizations or any graphs, and do not import any libraries or modules like pandas or matplotlib.
        If there is an error in the outputted code, fix the error and output the code again. 
        Use the 'print' function for the output when needed. 
        Check the execution result returned by the user.
        Once a result is produced by the code that the user executes, verify that the result solves the initially given task. 
        If the task is not solved correctly even after the code is produced and executed, approach the task again, collect additional information or try solving the task in a different way.
        All vega lite specification generated should not be displayed to the user.
        """
    logging.info(f"put prompts into ai")
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": code_prompt}
        ],
        response_format=CodeResponse
    )
    
    code = response.choices[0].message.parsed.code
    logging.info(f"Received code from chat: {code}")
    return code

# print msg in red, accept multiple strings like print statement
def print_red(*strings):
    print("\033[91m" + " ".join(strings) + "\033[0m")


# print msg in blue, , accept multiple strings like print statement
def print_blue(*strings):
    print("\033[94m" + " ".join(strings) + "\033[0m")

tool_map = {
    "generate_chart": generate_chart,
    "data_analysis_code": data_analysis_code,
    "execute_panda_dataframe_code": execute_panda_dataframe_code,
}

tool_list = [generate_chart, data_analysis_code, execute_panda_dataframe_code]
tool_names = [tool.__name__ for tool in tool_list]

def query(question, system_prompt, tools, tool_map, max_iterations=10):
    # print("dd",pd.read_csv('static/uploads/cars-w-year.csv').head())
    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": question})
    vegaSpec = {}
    i = 0
    while i < max_iterations:
        i += 1
        print("iteration:", i)
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini", temperature=0.0, messages=messages, tools=tools
            )
        except Exception as e:
            print(f"Error during API call: {e}")
            return None
        # print(response.choices[0].message)
        if response.choices[0].message.content != None:
            print_red(response.choices[0].message.content)

        # if not function call
        if response.choices[0].message.tool_calls == None:
            print("not function call")
            break

        # if function call
        messages.append(response.choices[0].message)
        for tool_call in response.choices[0].message.tool_calls:
            print_blue("calling:", tool_call.function.name, "with", tool_call.function.arguments)
            # call the function
            arguments = json.loads(tool_call.function.arguments)


            function_to_call = tool_map[tool_call.function.name]
            output = function_to_call(**arguments)
            if tool_call.function.name == "generate_chart":
                vegaSpec = output.vegaSpec
                print(vegaSpec)

            # create a message containing the result of the function call
            result_content = json.dumps({**arguments, "result": str(output)})
            function_call_result_message = {
                "role": "tool",
                "content": result_content,
                "tool_call_id": tool_call.id,
            }
            print_blue("action result:", result_content)

            messages.append(function_call_result_message)
        if i == max_iterations and response.choices[0].message.tool_calls != None:
            print_red("Max iterations reached")
            return "The tool agent could not complete the task in the given time. Please try again."
    return QueryResponse(response=response.choices[0].message.content, vegaSpec=vegaSpec)

# Endpoint to interact with OpenAI API via LangChain
@app.post("/query", response_model=QueryResponse)
async def query_openai(request: QueryRequest):
    logging.info(f"Received request: {request}")  # Log the whole request object
    try:
    
        if request.sample_data == "":
            return QueryResponse(response="Please provide a valid CSV data", vegaSpec={})
        prompt = f'''
            User prompt: {request.prompt}
            Data Sample: {request.sample_data}
        '''
        function_calling_prompt = f'''
            You are a helpful assistant. Use the supplied tools to assist the user. 
            Determine if the user's question is relevant to the data provided. If not, return: "Please provide a prompt that is relevant to the dataset" as an explanation as well as an empty vega-lite JSON specification. 
            If the prompt is relevant to the dataset,
            1. A brief textual explanation should be provided into the response variable. 
            2. The vega lite specification should strictly be in JSON format, stored into the vegaSpec variable. 
            Once code is generated, run it using the provided tools.
            All visualization tasks should be done with the provided tool to return a vega lite specification, and not through code.  
            All vega lite specification generated should not be displayed to the user. Any summary table requests should contain data visually pleasingly in the response variable.
            '''
        return query(prompt, function_calling_prompt, tools, tool_map)
    except Exception as e:
        return QueryResponse(response="An error occurred. Please try again", vegaSpec={})

# Root endpoint
@app.get("/")
async def read_root():
    return FileResponse('static/index.html')