from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv
import json 
import logging
from typing import List
from jsonschema import validate, ValidationError
import requests
import pandas as pd

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
    columns_info: List[ColumnInfo] 
    sample_data: str

class QueryResponse(BaseModel):
    response: str
    vegaSpec: dict
    cols: list

def validate_vega_lite_spec(spec: dict):
    try:
        schema = requests.get(VEGA_LITE_SCHEMA_URL).json()
        validate(instance=spec, schema=schema)
        return True
    except ValidationError as e:
        logging.error(f"Vega-Lite spec validation error: {str(e)}")
        return False

# Endpoint to interact with OpenAI API via LangChain
@app.post("/query", response_model=QueryResponse)
async def query_openai(request: QueryRequest):
    logging.info(f"Received request: {request}")  # Log the whole request object
    try:
        # Construct a prompt to send to OpenAI for Vega-Lite spec generation
        df = pd.DataFrame(json.loads(request.sample_data))
        if df.empty:
            return QueryResponse(response="Please provide a prompt and CSV data.", vegaSpec={})

        columns = df.columns.tolist()
        logging.info(f"Columns: {columns}")

        columns_description = {
            col.name: f"(type: {col.type})" for col in request.columns_info
        }

        relevant_columns_prompt = f"""
            Here is a sample of the full dataset: {df}. 
            Choose relevant columns of the dataset from {columns}, based on the user's prompt: {request.prompt}. At least 1 of the chosen columns must have type 'number'.
            Return the relevant columns in a list of strings separated by commas. Do not give reasons or descriptions.
        """

        column_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert in extracting relevant information and understanding datasets."},
                {"role": "user", "content": relevant_columns_prompt}
            ],
        )

        
        ai_column_response = column_response.choices[0].message.content.strip()
        
        # Remove any surrounding brackets, quotes, or extra spaces
        ai_column_response = ai_column_response.replace("[", "").replace("]", "").replace("'", "").strip()
        
        # Split the columns and clean up any extra spaces
        rel_columns = [col.strip() for col in ai_column_response.split(',')]

        logging.info(f"Relevant Columns: {rel_columns}")

        rel_df = df[rel_columns]
        rel_data = rel_df.to_csv(index=False)

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
            Your response must be a vega-lite JSON specification with one data point, and a description.
            """

        user_prompt = f"""
            Generate a JSON object with two fields:
            1. "vegaSpec": A valid Vega-Lite JSON specification with data from {rel_data} based on the prompt: {request.prompt}
            2. "response": A brief textual description explaining the graph.
            Make sure that the response is a properly formatted JSON object.
            """

        # Call the OpenAI API via LangChain
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                { "role": "user", "content": user_prompt}
            ],
            model="gpt-3.5-turbo",
        )
        logging.info(f"OpenAI API response: {chat_completion}")
        # Extract the response text from OpenAI
        ai_response = chat_completion.choices[0].message.content
        logging.info(f"Received response from OpenAI: {ai_response}")  # Log AI response

        # Assuming the AI responds with a JSON-like structure containing both the spec and response
        #ai_response_json = json.loads(ai_response)
        try:
            ai_response_json = json.loads(ai_response)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse AI response: {ai_response}")
            raise HTTPException(status_code=500, detail="Failed to parse AI response.")

        # Extract the Vega-Lite spec and the text response
        vega_spec = ai_response_json.get("vegaSpec", {})
        text_response = ai_response_json.get("response", {}) #.get("description", "Here is the chart based on your query.")
        if not validate_vega_lite_spec(vega_spec):
            return QueryResponse(
                response="The generated Vega-Lite specification is ill-formed and cannot be used. Please refine your query.",
                vegaSpec={}
            )
        return QueryResponse(response=text_response, vegaSpec=vega_spec, cols=rel_columns)
    except Exception as e:
        if type(e) is KeyError:
            return QueryResponse(response="Please try again, providing a relevant prompt.", vegaSpec={})
        return QueryResponse(response="Please try again, unfortunately an error occurred.", vegaSpec={})

# Root endpoint
@app.get("/")
async def read_root():
    return FileResponse('static/index.html')