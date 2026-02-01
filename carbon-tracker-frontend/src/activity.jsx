import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";

function Activity() {
  const [activityText, setActivityText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [username, setUsername] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const navigate = useNavigate();

  useEffect(() => {
    // 1. Check if user is logged in
    const storedUser = localStorage.getItem("username");
    if (!storedUser) {
      alert("You must log in first!");
      navigate("/"); 
    } else {
      setUsername(storedUser);
    }
  }, [navigate]);

  /**
   * STEP 2: CALCULATE CARBON
   * This sends the text from the box to the backend for analysis.
   */
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

      // Handle non-JSON responses gracefully (prevents Unexpected token '<' errors)
      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        const text = await response.text();
        console.error("Expected JSON but got:", text);
        throw new Error(`Server returned an error page (Status: ${response.status}). Ensure the backend is running and URLs are correct.`);
      }

      const data = await response.json();

      if (response.ok) {
        setResult(data);
        setActivityText("");
      } else {
        alert("Error: " + (data.message || "Unknown error"));
      }
    } catch (error) {
      console.error("Error logging activity:", error);
      alert(error.message || "Could not connect to server.");
    } finally {
      setLoading(false);
    }
  };

  /**
   * KEYBOARD HANDLER
   * Allows submitting by pressing Enter (without Shift)
   */
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault(); 
      handleLogActivity();
    }
  };

  // --- AUDIO RECORDING LOGIC ---

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
        
        // Cleanup microphone tracks
        stream.getTracks().forEach((t) => t.stop());
        
        // Start Step 1: Transcription
        transcribeAudio(blob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Microphone error:", err);
      alert("Could not access microphone. Please ensure permissions are granted in your browser settings.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current = null;
    }
  };

  /**
   * STEP 1: TRANSCRIBE SPEECH
   * Converts audio to text and puts it in the textarea.
   */
  const transcribeAudio = async (blob) => {
    setIsTranscribing(true);

    try {
      const formData = new FormData();
      formData.append('audio', blob, 'recording.webm');

      // Ensure this URL exactly matches your urls.py (including the trailing slash)
      const response = await fetch('http://localhost:8000/api/speech-to-text/', {
        method: 'POST',
        body: formData,
      });

      // Robust check for JSON content type
      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        const htmlError = await response.text();
        console.error("Backend returned HTML instead of JSON:", htmlError);
        
        // Custom message for 404s
        if (response.status === 404) {
          throw new Error("Endpoint /api/speech-to-text/ not found (404). Please rebuild your Docker backend.");
        }
        throw new Error(`Server Error (${response.status}). Check backend terminal logs.`);
      }

      const data = await response.json();

      if (response.ok && data.transcript) {
        setActivityText(data.transcript);
      } else {
        alert('Transcription failed: ' + (data.message || 'No speech detected.'));
      }
    } catch (error) {
      console.error('Transcription error:', error);
      alert(`Speech Service Error: ${error.message}`);
    } finally {
      setIsTranscribing(false);
    }
  };

  return (
    <div className="bg-gray-900 min-h-screen flex flex-col items-center justify-center px-6 py-12 text-white font-sans">
      <h1 className="text-4xl font-extrabold mb-8 tracking-tight" style={{ color: "#037880" }}>
        Carbon Activity Logger
      </h1>

      <div className="w-full max-w-2xl bg-gray-800 p-8 rounded-2xl shadow-2xl border border-gray-700">
        
        {/* TEXT AREA INPUT */}
        <label className="block text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          What did you do today?
        </label>
        <textarea
          value={activityText}
          onChange={(e) => setActivityText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Example: I drove 15km in a small car. I ate a beef burger."
          className="w-full px-5 py-4 rounded-xl border border-gray-600 bg-gray-900 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-all resize-none text-lg"
          rows={4}
        />
        <div className="flex justify-between mt-2">
            <span className="text-xs text-gray-500 italic">Pro-tip: Press Enter to calculate immediately.</span>
            {isTranscribing && (
                <span className="text-xs text-cyan-400 animate-pulse font-bold">Processing your voice...</span>
            )}
        </div>

        {/* VOICE CONTROLS */}
        <div className="mt-8 flex items-center justify-center space-x-6 border-t border-gray-700 pt-8">
          {!isRecording ? (
            <button
              onClick={startRecording}
              className="group flex flex-col items-center space-y-2 focus:outline-none"
            >
              <div className="w-16 h-16 bg-cyan-600 rounded-full flex items-center justify-center group-hover:bg-cyan-500 transition-colors shadow-lg">
                <span className="text-2xl">🎤</span>
              </div>
              <span className="text-xs font-bold text-cyan-400 group-hover:text-cyan-300">START VOICE</span>
            </button>
          ) : (
            <button
              onClick={stopRecording}
              className="group flex flex-col items-center space-y-2 focus:outline-none"
            >
              <div className="w-16 h-16 bg-red-600 rounded-full flex items-center justify-center animate-pulse shadow-lg">
                <span className="text-2xl">⏹️</span>
              </div>
              <span className="text-xs font-bold text-red-400">STOP & CONVERT</span>
            </button>
          )}
          
          {audioUrl && !isRecording && (
            <div className="hidden md:block">
               <audio src={audioUrl} controls className="h-8 opacity-50 hover:opacity-100 transition-opacity" />
            </div>
          )}
        </div>

        {/* CALCULATION BUTTON */}
        <button
          onClick={handleLogActivity}
          disabled={loading || isTranscribing || !activityText}
          className={`mt-10 w-full font-bold py-4 px-8 rounded-xl text-lg transition-all transform active:scale-95 shadow-xl ${
            loading || isTranscribing || !activityText
              ? "bg-gray-700 text-gray-500 cursor-not-allowed"
              : "bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white"
          }`}
        >
          {loading ? "Analyzing Data..." : "Calculate Carbon Footprint"}
        </button>
      </div>

      {/* RESULTS DISPLAY */}
      {result && (
        <div className="mt-10 w-full max-w-2xl animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="bg-gray-800 p-8 rounded-2xl border-l-8 border-green-500 shadow-2xl">
            <div className="flex justify-between items-start mb-4">
               <h3 className="text-2xl font-bold text-white">Impact Summary</h3>
               <span className="px-3 py-1 bg-green-900 text-green-300 text-xs font-bold rounded-full">LOGGED</span>
            </div>
            
            <div className="flex flex-col items-center py-4">
              <span className="text-6xl font-black text-green-400">
                {result.total_co2e_kg}
              </span>
              <span className="text-xl font-medium text-gray-400 mt-2">kg CO₂e Total Impact</span>
            </div>

            {result.activities && result.activities.length > 0 && (
              <div className="mt-6 space-y-3">
                <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest border-b border-gray-700 pb-2">Details</h4>
                {result.activities.map((act, idx) => (
                  <div key={idx} className="flex justify-between text-sm">
                    <span className="text-gray-300 capitalize">{act.activity_type}: {act.key}</span>
                    <span className="text-green-500 font-mono font-bold">+{act.co2e} kg</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="mt-12 flex space-x-6 text-sm">
        <Link to="/dashboard" className="text-gray-500 hover:text-white transition-colors underline decoration-gray-700">
          Back to Dashboard
        </Link>
        <button 
          onClick={() => {setResult(null); setActivityText("");}} 
          className="text-gray-500 hover:text-red-400 transition-colors"
        >
          Clear All
        </button>
      </div>
    </div>
  );
}

export default Activity;