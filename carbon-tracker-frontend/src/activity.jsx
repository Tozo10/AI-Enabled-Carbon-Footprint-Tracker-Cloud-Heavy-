import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

function Activity() {
  const [activityText, setActivityText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [username, setUsername] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    // 1. Check if user is logged in
    const storedUser = localStorage.getItem("username");
    if (!storedUser) {
      alert("You must log in first!");
      navigate("/"); // Kick them back to login page
    } else {
      setUsername(storedUser);
    }
  }, [navigate]);

  const handleLogActivity = async () => {
    if (!activityText) return;

    setLoading(true);
    setResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/log-activity/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username, // Send the valid username
          input_text: activityText,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setResult(data);
        setActivityText("");
      } else {
        alert("Error: " + data.message);
      }
    } catch (error) {
      console.error("Error logging activity:", error);
      alert("Could not connect to server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 min-h-screen flex flex-col items-center justify-center px-6 py-12 text-white">
      <h1 className="text-3xl font-bold mb-4" style={{ color: "#037880" }}>
        Log Your Activity
      </h1>

      <div className="w-full max-w-xl">
        <label className="block text-xl font-medium mb-2" style={{ color: "#037880" }}>
          Input text:
        </label>
        <textarea
          value={activityText}
          onChange={(e) => setActivityText(e.target.value)}
          placeholder="I drove 30km in a diesel car"
          className="w-full px-4 py-3 rounded-md border border-gray-600 bg-gray-800 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
          rows={3}
        />
      </div>

      <button
        onClick={handleLogActivity}
        disabled={loading}
        className={`mt-6 font-semibold py-2 px-6 rounded-md transition duration-300 ${
          loading ? "bg-gray-500" : "bg-blue-600 hover:bg-blue-700 text-white"
        }`}
      >
        {loading ? "Calculating..." : "Log Activity"}
      </button>

      {result && (
        <div className="mt-8 p-6 bg-gray-800 rounded-lg shadow-lg w-full max-w-xl border border-green-500">
          <h3 className="text-2xl font-bold text-green-400 mb-2">Result</h3>
          <p className="text-white text-lg">
            Activity: <span className="font-light">{result.activity}</span>
          </p>
          <p className="text-white text-lg mt-2">
            Carbon Footprint: <span className="text-3xl font-bold text-green-300">{result.co2e_kg} kg</span> CO₂e
          </p>
        </div>
      )}
      
      <Link to="/dashboard" className="mt-8 text-blue-400 hover:text-blue-300 underline">
        Back to Dashboard
      </Link>
    </div>
  );
}

export default Activity;