
import { useState } from 'react';
//const url = process.env.NODE_ENV === 'production' ? 'https://course-tools-demo.onrender.com/' : 'http://127.0.0.1:8000/';

function App() {
  const [message, setMessage] = useState("");
  //const [response, setResponse] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  
  function sendMessage() {
    if (message === "") {
      return;
    } 
    const userMessage = { text: message, sender: "user" }; // Add user message to chat history
    setChatHistory(prevHistory => [...prevHistory, userMessage]);

    try {
      // Simulate bot response
      const botResponse = {
        text: "I’m a simple bot. I don’t have real responses yet!",
        sender: "bot"
      };

      // Add bot response to chat history
      setChatHistory(prevHistory => [...prevHistory, botResponse]);
    } catch (error) {
      // Handle any errors
      console.error('Error simulating response:', error);
      const errorResponse = { text: "An error occurred. Please try again later.", sender: "bot", time: new Date().toLocaleTimeString() };
      setChatHistory(prevHistory => [...prevHistory, errorResponse]);
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
    }); //for fetching dynamic rersponse from backend*/
    setMessage("");
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

  return (
    <div className="container mx-auto mt-10">
    <h1 className="text-4xl mb-4">Chat Interface</h1>
    <div className="chat-box flex flex-col space-y-4">
      {chatHistory.map((entry, index) => (
        <div key={index} className={`chat ${entry.sender === 'user' ? 'chat-end' : 'chat-start'}`}>
          <div className="chat-image avatar">
            <div className="w-10 rounded-full">
              <img
                alt="Avatar"
                src={entry.sender === 'user'
                  ? "https://img.daisyui.com/images/stock/photo-1534528741775-53994a69daeb.webp" // User Avatar
                  : "https://img.daisyui.com/images/stock/photo-1534528741775-53994a69daeb.webp" // Bot Avatar (use different image if desired)
                }
              />
            </div>
          </div>
          <div className="chat-header">
            {entry.sender === 'user' ? 'You' : 'Bot'}
          </div>
          <div className="chat-bubble">{entry.text}</div>
          {/* Removed chat-footer */}
        </div>
      ))}
    </div>
    <div className="mt-5 flex gap-2">
      <input
        type="text"
        placeholder="Type your message here"
        value={message}
        className="input input-bordered w-full max-w-xs"
        onChange={handleMessage}
        onKeyDown={handleKeyPress}
      />
      <button className="btn" onClick={sendMessage}>Send</button>
    </div>
  </div>
);
}




/*     <div className="container mx-auto mt-10">
      <h1 className="text-4xl">Ask Anything!</h1>
      <div className="chat-box border p-4 mb-4 rounded bg-gray-100">
        {chatHistory.map((entry, index) => (
          <div key={index} className={`chat-message ${entry.sender === 'user' ? 'text-right' : 'text-left'}`}>
            <div className={`message ${entry.sender === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-300'}`}>
              {entry.text}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-5 flex gap-2">
        <input type="text" placeholder="Type your message here" value={message} className="input input-bordered w-full max-w-xs" onInput={handleMessage} />
        <button className="btn" onClick={sendMessage}>Send</button>
      </div>

      {/* <div className="card mt-10">
        <h2 className="text-xl">Response</h2>
        <div className="mt-5">
        🤖: {response}
        </div>
      </div>  }
    </div>
  );
} */

export default App;
