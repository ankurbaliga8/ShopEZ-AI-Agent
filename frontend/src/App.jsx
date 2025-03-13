import React, { useState, useEffect, useRef } from "react";
import {
  Paper,
  Box,
  TextField,
  Button,
  Typography,
  Avatar,
  CircularProgress,
} from "@mui/material";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import SendIcon from "@mui/icons-material/Send";
import DeleteIcon from "@mui/icons-material/Delete";

const API_URL = "http://127.0.0.1:8000/chat";
const ABORT_URL = "http://127.0.0.1:8000/abort";

function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "👋 Welcome to **Shop EZ AI Agent!** 🛍️ I help you find the best deals from Amazon & Walmart. What would you like to order today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);
  const inputRef = useRef(null); // ✅ Reference for input field

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput(""); // Clears input field
    setLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: input,
          user_id: "123", // Ensure this is always included
        }),
      });

      const data = await response.json();
      const botMessage = { role: "assistant", content: data.response };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `❌ Error: ${error.message}` },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus(); // ✅ Keep focus on input field
    }
  };

  const abortOrder = async () => {
    setMessages([
      {
        role: "assistant",
        content: "🚨 Order aborted. What would you like to order today?",
      },
    ]);

    try {
      await fetch(ABORT_URL, { method: "POST" });
    } catch (error) {
      console.error("Failed to abort order:", error);
    }
  };

  return (
    <>
      {/* Update Page Title */}
      <title>Shop EZ AI Agent - Smart Shopping Assistant</title>

      <div className="flex flex-col items-center justify-center min-h-screen bg-black text-white p-6">
        {/* Header */}
        <Box className="w-full max-w-lg bg-[#121212] p-4 rounded-t-lg flex items-center justify-center mb-1 shadow-lg">
          <Avatar className="bg-blue-500 mr-2">
            <ShoppingCartIcon />
          </Avatar>
          <Typography className="text-xl font-bold text-blue-400">
            Shop EZ AI Agent 🛍️
          </Typography>
        </Box>

        {/* Chat Box */}
        <Paper className="w-full max-w-lg p-6 rounded-xl shadow-lg bg-[#1E1E1E]">
          {/* Chat Window */}
          <Box className="h-80 overflow-y-auto border border-gray-600 rounded-lg p-3 bg-[#2C2C2C] mb-4">
            {messages.map((msg, index) => (
              <Box
                key={index}
                className={`flex mb-2 ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <Typography
                  className={`p-2 rounded-lg max-w-[75%] text-sm ${
                    msg.role === "user"
                      ? "bg-blue-500 text-white"
                      : "bg-gray-400 text-black"
                  }`}
                >
                  {msg.content}
                </Typography>
              </Box>
            ))}
            {loading && (
              <Box className="flex justify-center">
                <CircularProgress size={28} className="text-white" />
              </Box>
            )}
            <div ref={chatEndRef} />
          </Box>

          {/* Input Field */}
          <Box className="flex items-center gap-3 mt-2">
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Type your shopping list..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              className="bg-white text-black rounded-lg"
              inputRef={inputRef} // ✅ Keep reference
            />
            <Button
              variant="contained"
              color="primary"
              className="px-5 py-2 rounded-lg"
              onClick={sendMessage}
              endIcon={<SendIcon />}
            >
              Send
            </Button>
          </Box>

          {/* Abort Button */}
          <Box className="flex justify-center mt-4">
            <Button
              variant="contained"
              color="error"
              className="px-5 py-2 rounded-lg"
              onClick={abortOrder}
              startIcon={<DeleteIcon />}
            >
              Abort Order
            </Button>
          </Box>
        </Paper>

        {/* Footer */}
        <Box className="w-full max-w-lg text-center mt-6 p-4 rounded-b-lg bg-[#121212] shadow-lg">
          <Typography variant="body2" className="text-gray-400">
            Developed by <strong>Ankur Baliga</strong> 🚀
          </Typography>
          <Box className="flex justify-center gap-4 mt-2">
            <a
              href="https://www.linkedin.com/in/ankurbaliga/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:underline"
            >
              LinkedIn
            </a>
            <span className="text-gray-500">|</span>
            <a
              href="https://github.com/ankurbaliga8"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:underline"
            >
              GitHub
            </a>
          </Box>
          <Typography variant="body2" className="text-gray-500 mt-2 text-sm">
            © 2025 Shop EZ AI Agent| All Rights Reserved
          </Typography>
        </Box>
      </div>
    </>
  );
}

export default App;
