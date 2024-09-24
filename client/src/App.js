
import { useState } from 'react';
import { useEffect, useRef } from 'react';
import { csvParse, autoType } from 'd3-dsv'; //import d3-dsv for CSV parsing
import { VegaLite } from 'react-vega';

const url = process.env.NODE_ENV === 'production' ? 'https://course-tools-demo.onrender.com/' : 'http://127.0.0.1:8000/';

function App() {
  const [message, setMessage] = useState("");
  //const [response, setResponse] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [fileData, setFileData] = useState(null);
  const [fileError, setFileError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [showTable, setShowTable] = useState(false); // table visibility
  const [columnsInfo, setColumnsInfo] = useState(null); // To store columns and data types
  const [vegaSpec, setVegaSpec] = useState(null);
  
  //handle file upload and csv parsing
  const handleFileUpload = (file) => {
    if (file && file.name.endsWith('.csv')) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const text = event.target.result;
        const parsedData = csvParse(text, autoType);
        setFileData(parsedData);
        setFileError(""); //clear error messages
        setShowTable(true); //Show table after a successful upload
      };
      reader.readAsText(file);
    } else {
      setFileError("Please upload a valid CSV file.");
      setFileData(null); //clear previous data
      setShowTable(false); // Hide table if upload fails
    }
  };

  // Handle drag events
  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => {
    setDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    handleFileUpload(file);
  };

  const handleFileInputChange = (e) => {
    const file = e.target.files[0];
    handleFileUpload(file);
  };


  //send message to backend
  function sendMessage() {
    if (message === "") {
      return;
    } 
    const userMessage = { text: message, sender: "user" }; // add user message to chat history
    setChatHistory(prevHistory => [...prevHistory, userMessage]);
    setMessage(""); //reset to no message
  
    // Add empty bot message as a placeholder in chat history
    const botMessage = { text: "", sender: "bot" };
    setChatHistory(prevHistory => [...prevHistory, botMessage]);
  
    fetch(`${url}query`, {
      method: 'POST',
      body: JSON.stringify({ prompt: message }),
      headers: {
        'Content-Type': 'application/json'
      }
    }).then(response => response.json())
      .then(data => {
        const botFullResponse = data.response;

        //check if reseponse is Vega-Lite spec
        if (data.vegaSpec) {
          setVegaSpec(data.vegaSpec); // Store Vega-Lite spec for rendering
        } else {
  
          let currentIndex = 0;
          const words = botFullResponse.split(" "); //split bot message by word
    
          // Update bot's message progressively
          const intervalId = setInterval(() => {
            currentIndex++;
    
            // Update bot's message by each word
            const updatedText = words.slice(0, currentIndex).join(" ");
    
            // Update the last message in chatHistory with the updated text
            setChatHistory(prevHistory => {
              const newHistory = [...prevHistory];
              const lastMessageIndex = newHistory.length - 1;
    
              if (newHistory[lastMessageIndex].sender === "bot") {
                newHistory[lastMessageIndex] = {
                  ...newHistory[lastMessageIndex],
                  text: updatedText
                };
              }
              return newHistory;
            });
    
            // Stop interval when full message is typed out
            if (currentIndex === words.length) {
              clearInterval(intervalId);
            }
          }, 300); // interval time (300ms for each word)
        }
      });
  }

  function handleMessage(e) {   
    setMessage(e.target.value); 
  }

  function handleKeyPress(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault(); // Prevent the default action (e.g., form submission)
      sendMessage();
    }
  }

  const chatEndRef = useRef(null);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory]);

  return (
    <div className="flex flex-col h-screen">
      <div className="sticky top-0 p-4 z-20 bg-base-100">
        <h1 className="text-4xl mb-4">AI Assistant</h1>
      </div>
      {/* File Upload Section */}
      <div className="sticky top-16 p-4 z-10 bg-base-100">
        <div
          className={`p-6 border-2 border-dotted rounded-md mx-auto text-center transition-colors 
            ${dragging ? 'bg-base-300' : 'bg-base-200'} w-1/2`} // Use DaisyUI's base color classes
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input
            type="file"
            accept=".csv"
            className="hidden"
            id="file-upload"
            onChange={handleFileInputChange}
          />
          <label
            htmlFor="file-upload"
            className="cursor-pointer p-2 block"
          >
            {fileData ? (
              <span>CSV File Uploaded! Drag & Drop or Click for New File Upload</span>
            ) : (
              <span>Drag & Drop or Click to Upload CSV File</span>
            )}
          </label>
          {fileError && <p className="text-error">{fileError}</p>} {/* Use DaisyUI's text-error class */}
        </div>
          
        {/* Toggle Button to Show/Hide Table */}
        {fileData && (
          <div className="mt-4 text-center">
            <button
              className="btn btn-primary"
              onClick={() => setShowTable(!showTable)} // Toggle the table visibility
            >
              {showTable ? "Hide Data Table" : "Show Data Table"}              </button>
          </div>
        )}
      </div>

      {/* Data Table (outside the upload section) */}
      {fileData && showTable && (
        <div className="mx-auto w-3/4 p-4">
          <h3 className="text-lg font-bold mb-4">Data Preview (first 5 rows):</h3>
          <table className="table w-full">
            <thead>
              <tr>
                {Object.keys(fileData[0]).map((key, index) => (
                  <th key={index}>{key}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {fileData.slice(0, 5).map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {Object.values(row).map((value, colIndex) => (
                    <td key={colIndex}>{value}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="w-custom-md lg:w-custom-lg mx-auto p-4">
          <div className="chat-box flex flex-col space-y-4">
            {chatHistory.map((entry, index) => (
              <div key={index} className={`chat ${entry.sender === 'user' ? 'chat-end' : 'chat-start'}`}>
                <div className="chat-image avatar">
                  <div
                    className="w-10 h-10 rounded-full"
                    style={{
                      backgroundColor: entry.sender === 'user' ? '#307D7E' : '#30748B' // Different colors for user and bot
                    }}
                  />
                </div>

                <div className="chat-header">
                  {entry.sender === 'user' ? 'You' : 'Bot'}
                </div>
                <div className="chat-bubble">{entry.text}</div>
              </div>
            ))}
            <div ref={chatEndRef} /> {/* Scroll to this element */}
          </div>
        </div>
      </div>

      {/* Input Field */}
      <div className="p-4 border-t">
        <div className="w-custom-md lg:w-custom-lg mx-auto">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Type your message here"
              value={message}
              className="input input-bordered flex-grow"
              onChange={handleMessage}
              onKeyDown={handleKeyPress}
            />
            <button className="btn flex-shrink-0" onClick={sendMessage}>Send</button>
          </div>
        </div>
      </div>
    </div>
  );
}


export default App;
