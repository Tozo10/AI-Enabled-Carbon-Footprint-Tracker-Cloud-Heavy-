import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { faCheckCircle, faClock } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function ActivitiesList() {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchActivities = async () => {
    const username = localStorage.getItem("username");
    const token = localStorage.getItem("access_token");

    if (!username || !token) {
      navigate("/");
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/my-activities/`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (response.status === 401 || response.status === 403) {
        alert("Session expired. Please log in again.");
        localStorage.removeItem("access_token");
        localStorage.removeItem("username");
        navigate("/");
        return;
      }

      const data = await response.json();

      if (response.ok) {
        setActivities(data.activities || []);
      } else {
        console.error("Failed to fetch:", data.message);
      }
    } catch (error) {
      console.error("Error connecting to server:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivities();
  }, [navigate]);

  return (
    <div className="bg-gray-900 min-h-screen p-8 text-white">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold" style={{ color: "#037880" }}>Your Carbon History</h1>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchActivities}
              disabled={loading}
              className="px-4 py-2 rounded transition font-medium bg-[#037880] hover:bg-[#0497a1] disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>
            <Link to="/dashboard" className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded transition">
              Back to Dashboard
            </Link>
          </div>
        </div>

        {loading ? (
          <p className="text-center text-blue-300">Loading your history...</p>
        ) : activities.length === 0 ? (
          <div className="text-center py-10 bg-gray-800 rounded-lg">
            <p className="text-xl text-gray-400">No activities logged yet.</p>
            <Link to="/activity" className="text-blue-400 underline mt-2 inline-block">Log your first activity now!</Link>
          </div>
        ) : (
          <div className="bg-gray-800 rounded-lg shadow-lg overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-gray-700 text-gray-300">
                <tr>
                  <th className="p-4 text-center">Status</th>
                  <th className="p-4">Input</th>
                  <th className="p-4">Type</th>
                  <th className="p-4">Quantity</th>
                  <th className="p-4">Carbon (CO2e)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {activities.map((act) => (
                  <tr key={act._id || act.id || act.timestamp} className="hover:bg-gray-750 transition">
                    <td className="p-4 text-center">
                      {act.is_verified ? (
                        <span title="Government Verified (CEA/BEE India)">
                          <FontAwesomeIcon icon={faCheckCircle} className="text-green-500" />
                        </span>
                      ) : (
                        <span title="User Added (Pending Review)">
                          <FontAwesomeIcon icon={faClock} className="text-yellow-500 opacity-70" />
                        </span>
                      )}
                    </td>

                    <td className="p-4 text-gray-300 italic">"{act.input_text}"</td>
                    <td className="p-4 font-semibold text-blue-300">{act.activity_type}</td>
                    <td className="p-4 text-gray-400">{act.quantity} {act.unit}</td>
                    <td className="p-4 font-bold text-green-400">
                      {parseFloat(act.co2e).toFixed(2)} kg
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default ActivitiesList;
