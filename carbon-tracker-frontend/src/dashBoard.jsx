import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTrophy } from '@fortawesome/free-solid-svg-icons';
import './dashboard.css';

function Dashboard() {
  const [username, setUsername] = useState("Guest");
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // API Base URL from Docker environment variables
  const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  useEffect(() => {
    // 1. Handle Authentication / Identity
    const storedUser = localStorage.getItem("username");
    if (storedUser) {
      setUsername(storedUser);
    } else {
      if (import.meta.env.MODE === 'development') {
        setUsername("DevUser");
        localStorage.setItem("username", "DevUser");
      } else {
        navigate("/");
      }
    }
    
    // 2. Initial fetch of leaderboard data
    fetchLeaderboard();
  }, [navigate]);

  const fetchLeaderboard = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/leaderboard/`);
      const data = await response.json();
      if (data.status === "success") {
        setLeaderboard(data.leaderboard);
      }
    } catch (error) {
      console.error("Error fetching leaderboard from Cloudant:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("username");
    navigate("/");
  };

  // Toggle leaderboard and refresh data when opening
  const toggleLeaderboard = () => {
    if (!showLeaderboard) {
      fetchLeaderboard();
    }
    setShowLeaderboard(!showLeaderboard);
  };

  return (
    <div className="bg-gray-900 min-h-screen flex flex-col text-white relative">
      {/* Leaderboard Toggle Button */}
      <button
        onClick={toggleLeaderboard}
        className="absolute top-6 right-6 hover:cursor-pointer text-white font-semibold py-2 px-4 rounded-full transition duration-300 z-50 text-2xl"
        title={showLeaderboard ? "Hide Leaderboard" : "View Leaderboard"}
      >
        <FontAwesomeIcon 
          icon={faTrophy} 
          className={`text-2xl ${showLeaderboard ? 'text-yellow-400' : 'text-white'}`} 
        />
      </button>

      {/* Main Layout */}
      <div className="flex flex-1">
        {/* Main Content Section */}
        <div className={`flex flex-col items-center justify-center px-6 py-12 transition-all duration-500 ${showLeaderboard ? 'w-2/3' : 'w-full'}`}>
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold mb-2 animate-fadeSlide" style={{ color: "#037880" }}>
              Welcome, {username}!
            </h1>
            <p className="text-blue-300 text-lg max-w-xl animate-fadeSlide">
              Ready to take climate action today? Choose an option below to get started.
            </p>
          </div>

          {/* Action Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-3xl">
            <Link to="/activity" className="bg-white text-gray-800 rounded-lg shadow-md p-6 hover:bg-blue-100 transition duration-300">
              <h2 className="text-xl font-semibold mb-2">Log a New Activity</h2>
              <p className="text-sm">Track your travel, energy use, or other carbon-impacting actions.</p>
            </Link>

            <Link to="/activities" className="bg-white text-gray-800 rounded-lg shadow-md p-6 hover:bg-green-100 transition duration-300">
              <h2 className="text-xl font-semibold mb-2">Show Previous Activities</h2>
              <p className="text-sm">Review your carbon footprint history and insights.</p>
            </Link>

            <button 
              onClick={handleLogout}
              className="bg-red-500 text-white rounded-lg shadow-md p-6 hover:bg-red-600 transition duration-300 text-left"
            >
              <h2 className="text-xl font-semibold mb-2">Logout</h2>
              <p className="text-sm">Securely end your session and return to login.</p>
            </button>
          </div>
        </div>

        {/* Dynamic Leaderboard Sidebar */}
        {showLeaderboard && (
          <div className="w-1/3 bg-gray-800 shadow-lg p-6 border-l-4 border-blue-500 overflow-y-auto animate-fadeSlide">
            <h2 className="text-2xl font-bold mb-4" style={{ color: "#037880" }}>
              🌍 Top Climate Champions
            </h2>
            <p className="text-gray-400 mb-6 text-sm">
              Real-time leaders based on total recorded carbon activities.
            </p>
            
            <div className="space-y-3">
              {loading ? (
                <div className="text-center py-10">
                  <p className="text-blue-400 animate-pulse">Loading data from Cloudant...</p>
                </div>
              ) : leaderboard.length > 0 ? (
                leaderboard.map((leader) => (
                  <div
                    key={leader.rank}
                    className="bg-gray-700 rounded-lg p-4 hover:bg-gray-600 transition duration-200 border border-gray-600"
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-2xl">{leader.medal}</span>
                      <div className="flex-1">
                        <p className="font-semibold text-white text-sm">
                          {leader.name} {leader.name === username && "(You)"}
                        </p>
                      </div>
                      <div className="bg-blue-500 text-white font-bold text-xs py-1 px-2 rounded-full">
                        #{leader.rank}
                      </div>
                    </div>
                    <p className="text-xs text-gray-300 ml-10">{leader.contribution}</p>
                  </div>
                ))
              ) : (
                <div className="bg-gray-700 rounded-lg p-6 text-center border border-dashed border-gray-500">
                  <p className="text-gray-400">No activity logs found yet. Start logging to appear here!</p>
                </div>
              )}
            </div>

            <div className="mt-6 pt-4 border-t border-gray-600 text-center">
              <button 
                onClick={fetchLeaderboard}
                className="text-xs text-blue-400 hover:text-blue-300 underline"
              >
                Refresh Leaderboard
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;