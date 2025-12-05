import React, { useState } from "react";
import './aboutText.css'
import './index.css'
import { useNavigate } from "react-router-dom";

function AuthForm() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("login"); // 'login' or 'signup'
  const [isLoading, setIsLoading] = useState(false);

  // State for form data
  const [formData, setFormData] = useState({
    username: "",
    password: "",
    confirm: ""
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    // 1. Point to the correct API endpoint
    const endpoint = mode === "login" 
      ? "http://localhost:8000/api/login/" 
      : "http://localhost:8000/api/register/"; // Make sure this matches urls.py

    try {
      // 2. Send the data to your Django Backend
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: formData.username,
          password: formData.password
        }),
      });

      const data = await response.json();

      // 3. CRITICAL: Check if the backend said "OK"
      if (response.ok) {
        console.log("Success:", data);
        
        // Save the valid username for the Activity Page to use
        localStorage.setItem("username", data.username);
        
        // Redirect to Dashboard
        navigate("/dashboard");
      } else {
        // 4. If failed, show alert and DO NOT redirect
        alert("Error: " + (data.message || "Invalid credentials. Please try again."));
      }

    } catch (error) {
      console.error("Login Error:", error);
      alert("Could not connect to server. Is Docker running?");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 min-h-screen flex items-center justify-between px-8">
      <div className="text-2xl text-blue-300 px-4 py-10 w-1/2">
        <h1 className="typewriter">AI-Enabled Carbon Footprint Tracker</h1>
        <p className="about-text">
          The AI-Enabled Carbon Footprint Tracker is an intelligent, cloud-native web application...
        </p>
      </div>

      <div className="bg-white p-8 rounded shadow-md w-96">
        <h3 className="text-xl font-bold mb-4">{mode === "login" ? "Login" : "Sign Up"}</h3>

        {/* Toggle Mode */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700">Choose Mode</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border rounded-md"
          >
            <option value="login">Login</option>
            <option value="signup">Sign Up</option>
          </select>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700">Username</label>
            <input 
              type="text" 
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder="Enter Username" 
              className="mt-1 block w-full px-3 py-2 border rounded-md" 
              required
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input 
              type="password" 
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Password" 
              className="mt-1 block w-full px-3 py-2 border rounded-md" 
              required
            />
          </div>

          {mode === "signup" && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700">Confirm Password</label>
              <input 
                type="password" 
                name="confirm"
                value={formData.confirm}
                onChange={handleChange}
                placeholder="Confirm Password" 
                className="mt-1 block w-full px-3 py-2 border rounded-md" 
                required
              />
            </div>
          )}

          <button 
            type="submit" 
            disabled={isLoading}
            className={`w-full text-white py-2 rounded ${isLoading ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700'}`}
          >
            {isLoading ? "Processing..." : (mode === "login" ? "Login" : "Sign Up")}
          </button>
        </form>
      </div>
    </div>
  );
}

export default AuthForm;