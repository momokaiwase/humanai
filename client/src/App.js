
import { useState } from 'react';
import { useEffect, useRef } from 'react';
//const url = process.env.NODE_ENV === 'production' ? 'https://course-tools-demo.onrender.com/' : 'http://127.0.0.1:8000/';

function App() {
  const [message, setMessage] = useState("");
  //const [response, setResponse] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  
  function sendMessage() {
    if (message === "") {
      return;
    } 
    const userMessage = { text: message, sender: "user" }; // add user message to chat history
    setChatHistory(prevHistory => [...prevHistory, userMessage]);
    setMessage(""); //reset to no message
    
    // Simulated bot response (full message)
    const botFullResponse = "I’m a simple bot. I don’t have real responses yet!";
    const botMessage = { text: "", sender: "bot" };
    setChatHistory(prevHistory => [...prevHistory, botMessage]); // empty bot message = placeholder

    let currentIndex = 0;
    const words = botFullResponse.split(" "); //split bot message by word

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
    }, 300); // interval time (500ms for each word)
  }


    /* fetch(`${url}query`, {
      method: 'POST',
      body: JSON.stringify({ prompt: message }),
      headers: {
        'Content-Type': 'application/json'
      }
    }).then(response => {
      return response.json();
    }).then(data => {
      setResponse(data.response);
    }); //for fetching dynamic rersponse from backend
    setMessage("");
  }*/
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
      <div className="sticky top-0 p-4 z-10">
        <h1 className="text-4xl mb-4">AI Assistant</h1>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {/* Chat History */}
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
