import React, { useState } from "react";
import './aboutText.css'
import './index.css'
import { useNavigate } from "react-router-dom";

function AuthForm() {
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    // ✅ Add your login logic here
    navigate("/dashboard"); // redirect after login
  };

  const [mode, setMode] = useState("login");

  return (
    
    <div className="bg-gray-900 min-h-screen flex items-center justify-between px-8">
        <div className="text-2xl text-blue-300 px-4 py-10 w-1/2">
        <h1 className="typewriter">AI-Enabled Carbon Footprint Tracker</h1>
          <p className="about-text">
                The AI-Enabled Carbon Footprint Tracker is an intelligent, cloud-native web application designed to empower individuals to take meaningful climate action. The platform allows users to effortlessly track, understand, and reduce their daily carbon footprint by logging activities like travel and energy consumption through intuitive text or voice commands.
            </p>
        </div>
      <div className="bg-white p-8 rounded shadow-md w-96">
        <h3 className="text-xl font-bold mb-4">{mode === "login" ? "Login" : "Sign Up"}</h3>

        {/* Mode Selector */}
        <div className="mb-4">
          <label htmlFor="mode" className="block text-sm font-medium text-gray-700">Choose Mode</label>
          <select
            id="mode"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border rounded-md"
          >
            <option value="login">Login</option>
            <option value="signup">Sign Up</option>
          </select>
        </div>

        {/* Form */}
        <form>
          <div className="mb-4">
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">Email</label>
            <input type="email" id="email" name="email" placeholder="Email" className="mt-1 block w-full px-3 py-2 border rounded-md" />
          </div>
          {mode === "signup" && (
            <div className="mb-4">
              <label htmlFor="username" className="block text-sm font-medium text-gray-700">Username</label>
              <input
                type="text"
                id="username"
                name="username"
                placeholder="Username"
                className="mt-1 block w-full px-3 py-2 border rounded-md"
              />
            </div>
          )}

          <div className="mb-4">
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">Password</label>
            <input type="password" id="password" name="password" placeholder="Password" className="mt-1 block w-full px-3 py-2 border rounded-md" />
          </div>

          {mode === "signup" && (
            <div className="mb-4">
              <label htmlFor="confirm" className="block text-sm font-medium text-gray-700">Confirm Password</label>
              <input type="password" id="confirm" name="confirm" placeholder="Confirm Password" className="mt-1 block w-full px-3 py-2 border rounded-md" />
            </div>
          )}

          <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
            {mode === "login" ? "Login" : "Sign Up"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default AuthForm;