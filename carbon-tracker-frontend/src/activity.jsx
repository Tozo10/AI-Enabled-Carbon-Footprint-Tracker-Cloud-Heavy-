import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";

function Activity() {
  const [activityText, setActivityText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [username, setUsername] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
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
          username: username,
          input_text: activityText,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setResult(data);
        setActivityText("");
      } else {
        alert("Error: " + (data.message || "Unknown error"));
      }
    } catch (error) {
      console.error("Error logging activity:", error);
      alert("Could not connect to server.");
    } finally {
      setLoading(false);
    }
  };

  // --- Microphone recording handlers ---
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) audioChunksRef.current.push(ev.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        // stop all tracks
        stream.getTracks().forEach((t) => t.stop());
        // auto-upload after stop
        uploadAudio(blob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Microphone error:", err);
      alert("Could not access microphone. Please allow microphone access in your browser.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current = null;
    }
  };

  const uploadAudio = async (blob) => {
    if (!username) {
      alert('No username found. Please login first.');
      return;
    }

    setIsUploading(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('audio', blob, 'recording.webm');

      const response = await fetch('http://localhost:8000/api/log-activity-audio/', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        setResult(data);
      } else {
        alert('Error: ' + (data.message || 'Audio processing failed'));
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Could not upload audio to server.');
    } finally {
      setIsUploading(false);
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
          placeholder="I drove 10km in a cab. I ate 2 burgers."
          className="w-full px-4 py-3 rounded-md border border-gray-600 bg-gray-800 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
          rows={3}
        />
      </div>

      {/* --- Microphone Recording Controls --- */}
      <div className="w-full max-w-xl mt-6">
        <label className="block text-lg font-medium mb-2" style={{ color: "#037880" }}>
          Or record your activity (microphone):
        </label>

        <div className="flex items-center space-x-3">
          {!isRecording ? (
            <button
              onClick={startRecording}
              className="font-semibold py-2 px-4 rounded-md bg-green-600 hover:bg-green-700 text-white"
            >
              Start Recording
            </button>
          ) : (
            <button
              onClick={stopRecording}
              className="font-semibold py-2 px-4 rounded-md bg-red-600 hover:bg-red-700 text-white"
            >
              Stop Recording
            </button>
          )}

          {isUploading && (
            <span className="text-sm text-yellow-300">Uploading audio...</span>
          )}

          {audioUrl && (
            <audio className="ml-4" controls src={audioUrl} />
          )}
        </div>
        <p className="text-xs text-gray-400 mt-2">Tip: After stopping, the recording will be uploaded automatically.</p>
      </div>

      <button
        onClick={handleLogActivity}
        disabled={loading}
        className={`mt-6 font-semibold py-2 px-6 rounded-md transition duration-300 ${
          loading ? "bg-gray-500" : "bg-blue-600 hover:bg-blue-700 text-white"
        }`}
      >
        {loading ? "Calculating..." : "Calculate Carbon Footprint"}
      </button>

      {/* --- RESULT SECTION (Updated) --- */}
      {result && (
        <div className="mt-8 w-full max-w-xl space-y-4">
          
          {/* 1. Total Summary Box */}
          <div className="p-6 bg-gray-800 rounded-lg shadow-lg border border-green-500 text-center">
            <h3 className="text-xl font-bold text-green-400 mb-2">Total Impact</h3>
            <p className="text-white text-lg">
              <span className="text-4xl font-bold text-green-300">
                {result.total_co2e_kg}
              </span>{" "}
              kg CO₂e
            </p>
            <p className="text-sm text-gray-400 mt-2">{result.message}</p>
          </div>

          {/* 2. Individual Item Breakdown (If multiple sentences) */}
          {result.activities && result.activities.length > 0 && (
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <h4 className="text-gray-400 text-sm uppercase tracking-wide mb-3">Breakdown</h4>
              <ul className="space-y-3">
                {result.activities.map((item, index) => (
                  <li key={index} className="flex justify-between items-center border-b border-gray-700 pb-2 last:border-0">
                    <div>
                      <span className="block font-medium text-white capitalize">
                        {item.activity_type} ({item.key})
                      </span>
                      <span className="text-xs text-gray-400">
                        {item.quantity} {item.unit}
                      </span>
                    </div>
                    <span className="font-bold text-green-400">
                      {item.co2e} kg
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <Link to="/dashboard" className="mt-8 text-blue-400 hover:text-blue-300 underline">
        Back to Dashboard
      </Link>
    </div>
  );
}

export default Activity;