import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTrophy } from '@fortawesome/free-solid-svg-icons';
import { faGlobe } from '@fortawesome/free-solid-svg-icons';
import './dashboard.css';

function Dashboard() {
  const [username, setUsername] = useState("Guest");
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const navigate = useNavigate();

  // Mock leaderboard data - replace with actual API call
  const leaderboardData = [
    { rank: 1, name: "Sarah Green", contribution: "2,450 kg CO₂ reduced", medal: "🥇" },
    { rank: 2, name: "John Eco", contribution: "2,180 kg CO₂ reduced", medal: "🥈" },
    { rank: 3, name: "Emma Climate", contribution: "1,920 kg CO₂ reduced", medal: "🥉" },
    { rank: 4, name: "Mike Earth", contribution: "1,650 kg CO₂ reduced", medal: "4️⃣" },
    { rank: 5, name: "Lisa Nature", contribution: "1,340 kg CO₂ reduced", medal: "5️⃣" }
  ];

  useEffect(() => {
    // 1. Get the real username from Local Storage
    const storedUser = localStorage.getItem("username");
    if (storedUser) {
      setUsername(storedUser);
    } else {
      // Development mode: bypass auth, use test user
      // For production, this should redirect to login
      if (import.meta.env.MODE === 'development') {
        setUsername("DevUser");
        localStorage.setItem("username", "DevUser");
      } else {
        navigate("/");
      }
    }
  }, [navigate]);

  const handleLogout = () => {
    // 2. Clear session data
    localStorage.removeItem("username");
    navigate("/");
  };

  return (
    <div className="bg-gray-900 min-h-screen flex flex-col text-white relative">
      {/* Leaderboard Button - Top Right Corner */}
      <button
        onClick={() => setShowLeaderboard(!showLeaderboard)}
        className="absolute top-6 right-6  hover:cursor-pointer text-white font-semibold py-2 px-4 rounded-full transition duration-300 z-50 text-2xl"
        title={showLeaderboard ? "Hide Leaderboard" : "View Leaderboard"}
      >
        <FontAwesomeIcon icon={faTrophy} className="text-2xl text-white" />
      </button>

      {/* Main Layout: Content + Leaderboard Sidebar */}
      <div className="flex flex-1">
        {/* Main Content Section - 2/3 width when leaderboard is open, full width when closed */}
        <div className={`flex flex-col items-center justify-center px-6 py-12 ${showLeaderboard ? 'w-2/3' : 'w-full'}`}>
          {/* Welcome Message */}
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

            {/* Link to the new Activities List Page */}
            <Link to="/activities" className="bg-white text-gray-800 rounded-lg shadow-md p-6 hover:bg-green-100 transition duration-300">
              <h2 className="text-xl font-semibold mb-2">Show Previous Activities</h2>
              <p className="text-sm">Review your carbon footprint history and insights.</p>
            </Link>

            {/* Logout Button */}
            <button 
              onClick={handleLogout}
              className="bg-red-500 text-white rounded-lg shadow-md p-6 hover:bg-red-600 transition duration-300 text-left"
            >
              <h2 className="text-xl font-semibold mb-2">Logout</h2>
              <p className="text-sm">Securely end your session and return to login.</p>
            </button>
          </div>
        </div>

        {/* Leaderboard Sidebar - Right side, 1/3 width */}
        {showLeaderboard && (
          <div className="w-1/3 bg-gray-800 shadow-lg p-6 border-l-4 border-blue-500 overflow-y-auto animate-fadeSlide">
            <h2 className="text-2xl font-bold mb-4" style={{ color: "#037880" }}>
              🌍 Top 5 Climate Champions
            </h2>
            <p className="text-gray-400 mb-6 text-sm">
              Leaders who have contributed the most to reducing carbon emissions
            </p>
            
            <div className="space-y-3">
              {leaderboardData.map((leader) => (
                <div
                  key={leader.rank}
                  className="bg-gray-700 rounded-lg p-4 hover:bg-gray-600 transition duration-200"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">{leader.medal}</span>
                    <div className="flex-1">
                      <p className="font-semibold text-white text-sm">{leader.name}</p>
                    </div>
                    <div className="bg-blue-500 text-white font-bold text-xs py-1 px-2 rounded-full">
                      #{leader.rank}
                    </div>
                  </div>
                  <p className="text-xs text-gray-300 ml-10">{leader.contribution}</p>
                </div>
              ))}
            </div>

            {/* Additional Stats */}
            <div className="mt-6 pt-4 border-t border-gray-600">
              <p className="text-center text-gray-400 text-xs">
                Total CO₂ Reduced by top users: <span className="text-green-400 font-bold">9,540 kg</span>
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;