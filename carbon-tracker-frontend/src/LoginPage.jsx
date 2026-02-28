import React, { useState } from "react";
import "./aboutText.css";
import "./index.css";
import { useNavigate } from "react-router-dom";

function AuthForm() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [isLoading, setIsLoading] = useState(false);

  const [formData, setFormData] = useState({
    username: "",
    password: "",
    confirm: "",
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    // Clear old tokens before new login
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");

    if (mode === "signup" && formData.password !== formData.confirm) {
      alert("Passwords do not match!");
      setIsLoading(false);
      return;
    }

    try {
      // -------------------------
      // STEP 1: Register (if signup)
      // -------------------------
      if (mode === "signup") {
        const registerResponse = await fetch(
          "http://localhost:8001/api/register/",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              username: formData.username,
              password: formData.password,
            }),
          }
        );

        if (!registerResponse.ok) {
          const errorData = await registerResponse.json();
          alert(errorData.message || "User already exists.");
          setIsLoading(false);
          return;
        }
      }

      // -------------------------
      // STEP 2: Login via JWT
      // -------------------------
      const loginResponse = await fetch(
        "http://localhost:8001/api/token/",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            username: formData.username,
            password: formData.password,
          }),
        }
      );

      const data = await loginResponse.json();

      if (loginResponse.ok) {
        // Store JWT tokens
        localStorage.setItem("access_token", data.access);
        localStorage.setItem("refresh_token", data.refresh);
        localStorage.setItem("username", formData.username);

        navigate("/dashboard");
      } else {
        alert("Invalid username or password.");
      }
    } catch (error) {
      console.error("Auth Error:", error);
      alert("Could not connect to Auth Service (Port 8001).");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 min-h-screen flex items-center justify-between px-8">
      <div className="text-2xl text-blue-300 px-4 py-10 w-1/2">
        <h1 className="typewriter">
          AI-Enabled Carbon Footprint Tracker
        </h1>
        <p className="about-text">
          The AI-Enabled Carbon Footprint Tracker is an intelligent,
          cloud-native web application...
        </p>
      </div>

      <div className="bg-white p-8 rounded shadow-md w-96">
        <h3 className="text-xl font-bold mb-4">
          {mode === "login" ? "Login" : "Sign Up"}
        </h3>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700">
            Choose Mode
          </label>
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
            <label className="block text-sm font-medium text-gray-700">
              Username
            </label>
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
            <label className="block text-sm font-medium text-gray-700">
              Password
            </label>
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
              <label className="block text-sm font-medium text-gray-700">
                Confirm Password
              </label>
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
            className={`w-full text-white py-2 rounded ${
              isLoading
                ? "bg-gray-400"
                : "bg-blue-600 hover:bg-blue-700"
            }`}
          >
            {isLoading
              ? "Processing..."
              : mode === "login"
              ? "Login"
              : "Sign Up"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default AuthForm;