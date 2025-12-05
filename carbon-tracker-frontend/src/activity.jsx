import React, { useState } from "react";

function Activity() {
  const [activityText, setActivityText] = useState("");

  const handleLogActivity = () => {
    // You can add logic here to send activityText to your backend or state
    console.log("Logged activity:", activityText);
    setActivityText(""); // Clear input after logging
  };

  return (
    <div className="bg-gray-900 min-h-screen flex flex-col items-center justify-center px-6 py-12 text-white">
      {/* Header */}
      <h1 className="text-3xl font-bold  mb-4 animate-fadeSlide" style={{color: "#037880"}}>
        Log Your Activity
      </h1>

      {/* Description */}
      <p className="text-blue-200 text-center max-w-xl mb-6 animate-fadeSlide">
        Describe your activity in a simple sentence (e.g., "I took a 15km cab ride").
      </p>

      {/* Input Box */}
      <div className="w-full max-w-xl">
        <label htmlFor="activity" className="block text-xl font-medium mb-2" style={{color: "#037880"}}>
          Input text:
        </label>
        <textarea
          id="activity"
          value={activityText}
          onChange={(e) => setActivityText(e.target.value)}
          placeholder="I took a 15km cab ride"
          className="w-full px-4 py-3 rounded-md border border-gray-300 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
          rows={3}
        />
      </div>

      {/* Button */}
      <button
        onClick={handleLogActivity}
        className="mt-6 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-md transition duration-300"
      >
        Log Activity
      </button>
    </div>
  );
}

export default Activity;
