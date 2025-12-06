import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

function ActivitiesList() {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const username = localStorage.getItem("username");
    if (!username) {
      navigate("/"); // Protect the route
      return;
    }

    // Fetch data from backend
    const fetchActivities = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/my-activities/?username=${username}`);
        const data = await response.json();

        if (response.ok) {
          setActivities(data.activities);
        } else {
          console.error("Failed to fetch:", data.message);
        }
      } catch (error) {
        console.error("Error connecting to server:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchActivities();
  }, [navigate]);

  return (
    <div className="bg-gray-900 min-h-screen p-8 text-white">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold" style={{ color: "#037880" }}>Your Carbon History</h1>
          <Link to="/dashboard" className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded transition">
            ← Back to Dashboard
          </Link>
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
                  <th className="p-4">Input</th>
                  <th className="p-4">Type</th>
                  <th className="p-4">Quantity</th>
                  <th className="p-4">Carbon (CO₂e)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {activities.map((act) => (
                  <tr key={act.id} className="hover:bg-gray-750 transition">
                    <td className="p-4 text-gray-300 italic">"{act.input_text}"</td>
                    <td className="p-4 font-semibold text-blue-300">{act.activity_type}</td>
                    <td className="p-4">{act.quantity} {act.unit}</td>
                    <td className="p-4 font-bold text-green-400">{act.co2e} kg</td>
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