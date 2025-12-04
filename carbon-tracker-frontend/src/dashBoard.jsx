import React from "react";
import { Link } from "react-router-dom";

import './dashboard.css'; // optional for custom animations

function Dashboard({ username="username" }) {
  return (
    <div className="bg-gray-900 min-h-screen flex flex-col items-center justify-center px-6 py-12 text-white">
      {/* Welcome Message */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-#037880 mb-2 animate-fadeSlide"  style={{ color: "#037880" }}
>
          Welcome, {username}!
        </h1>
        <p className="text-blue-300 text-lg max-w-xl animate-fadeSlide">
          Ready to take climate action today? Choose an option below to get started.
        </p>
      </div>

      {/* Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-3xl">
        <Link
          to="/activity" className="bg-white text-gray-800 rounded-lg shadow-md p-6 hover:bg-blue-100 transition duration-300">
          <h2 className="text-xl font-semibold mb-2">Log a New Activity</h2>
          <p className="text-sm">Track your travel, energy use, or other carbon-impacting actions.</p>
        </Link>

        <Link to="/activities" className="bg-white text-gray-800 rounded-lg shadow-md p-6 hover:bg-green-100 transition duration-300">
          <h2 className="text-xl font-semibold mb-2">Show Previous Activities</h2>
          <p className="text-sm">Review your carbon footprint history and insights.</p>
        </Link>

        {/* <button className="bg-red-500 text-white rounded-lg shadow-md p-6 hover:bg-red-600 transition duration-300">
          <h2 className="text-xl font-semibold mb-2">Logout</h2>
          <p className="text-sm">Securely end your session and return to login.</p>
        </button> */}
        <Link
          to="/"
          className="bg-red-500 text-white rounded-lg shadow-md p-6 hover:bg-red-600 transition duration-300"
        >
          <h2 className="text-xl font-semibold mb-2">Logout</h2>
          <p className="text-sm">Securely end your session and return to login.</p>
        </Link>

      </div>
    </div>
  );
}

export default Dashboard;