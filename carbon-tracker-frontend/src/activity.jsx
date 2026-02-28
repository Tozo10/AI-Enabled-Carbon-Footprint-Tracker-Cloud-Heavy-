import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faMicrophone, faCompactDisc, faPlusCircle } from '@fortawesome/free-solid-svg-icons';

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

  // --- CROWDSOURCING STATES ---
  const [showModal, setShowModal] = useState(false);
  const [customFactor, setCustomFactor] = useState({
    activity_type: 'TRANSPORT',
    key: '',
    co2e_per_unit: '',
    unit: 'km',
    source_reference: ''
  });

  useEffect(() => {
    const storedUser = localStorage.getItem("username");
    const token = localStorage.getItem("access_token");
    
    if (!storedUser || !token) {
      alert("You must log in first!");
      navigate("/");
    } else {
      setUsername(storedUser);
    }
  }, [navigate]);

  /**
   * API CALL: LOG ACTIVITY
   */
  const handleLogActivity = async () => {
    if (!activityText) return;

    const token = localStorage.getItem("access_token");
 
  
  // ADD THIS CHECK
  if (!token) {
    alert("Your session has expired. Please log in again.");
    navigate("/");
    return;
  }


    setLoading(true);
    setResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/log-activity/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`, // Crucial for your new JWT settings
        },
        body: JSON.stringify({
          username: username, // Cloudant depends on this
          input_text: activityText,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setResult(data);
        setActivityText("");
      } else {
        // If the token is expired, redirect to login
        if (response.status === 401 || response.status === 403) {
            alert("Session expired. Please log in again.");
            navigate("/");
        } else {
            alert("Error: " + (data.message || "Unknown error"));
        }
      }
    } catch (error) {
      console.error("Error logging activity:", error);
      alert("Could not connect to server.");
    } finally {
      setLoading(false);
    }
  };

  /**
   * API CALL: SUBMIT CUSTOM FACTOR
   */
  const handleCustomFactorSubmit = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem("access_token");

    try {
      const response = await fetch("http://localhost:8000/api/add-custom-factor/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(customFactor)
      });

      if (response.ok) {
        alert("Factor suggested successfully! It will appear as 'Pending' in your logs.");
        setShowModal(false);
        setCustomFactor({ activity_type: 'TRANSPORT', key: '', co2e_per_unit: '', unit: 'km', source_reference: '' });
      } else {
        const errorData = await response.json();
        alert("Error: " + JSON.stringify(errorData));
      }
    } catch (err) {
      console.error("Submission failed:", err);
    }
  };

  /**
   * AUDIO RECORDING & TRANSCRIPTION
   */
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
        setAudioUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach((t) => t.stop());
        transcribeAudio(blob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      alert("Microphone error. Please check permissions.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const transcribeAudio = async (blob) => {
    setIsTranscribing(true);
    try {
      const formData = new FormData();
      formData.append('audio', blob, 'recording.webm');
      const response = await fetch('http://localhost:8000/api/speech-to-text/', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (response.ok && data.transcript) {
        setActivityText(data.transcript);
      }
    } catch (error) {
      console.error('Transcription error:', error);
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleLogActivity();
    }
  };

  return (
    <div className="bg-gray-900 min-h-screen flex flex-col items-center justify-center px-6 py-12 text-white font-sans">
      <h1 className="text-4xl font-extrabold mb-8 tracking-tight" style={{ color: "#037880" }}>
        Carbon Activity Logger
      </h1>

      <div className="w-full max-w-2xl bg-gray-800 p-8 rounded-2xl shadow-2xl border border-gray-700 relative">
        <label className="block text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          What did you do today?
        </label>
        <textarea
          value={activityText}
          onChange={(e) => setActivityText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Example: I drove 15km in a small car. I ate a beef burger."
          className="w-full px-5 py-4 rounded-xl border border-gray-600 bg-gray-900 text-white focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-all resize-none text-lg"
          rows={4}
        />
        
        <div className="flex justify-between mt-2">
          <span className="text-xs text-gray-500 italic">Pro-tip: Press Enter to calculate.</span>
          {isTranscribing && <span className="text-xs text-cyan-400 animate-pulse font-bold">Processing voice...</span>}
        </div>

        {/* VOICE CONTROLS */}
        <div className="mt-8 flex items-center justify-center space-x-6 border-t border-gray-700 pt-8">
          {!isRecording ? (
            <button onClick={startRecording} className="group flex flex-col items-center space-y-2 focus:outline-none">
              <div className="w-16 h-16 bg-cyan-600 rounded-full flex items-center justify-center group-hover:bg-cyan-500 transition-colors shadow-lg">
                <FontAwesomeIcon icon={faMicrophone} className="text-2xl text-white" />
              </div>
              <span className="text-xs font-bold text-cyan-400 uppercase">Start Voice</span>
            </button>
          ) : (
            <button onClick={stopRecording} className="group flex flex-col items-center space-y-2 focus:outline-none">
              <div className="w-16 h-16 bg-red-600 rounded-full flex items-center justify-center animate-pulse shadow-lg">
                <FontAwesomeIcon icon={faCompactDisc} className="text-2xl text-white" />
              </div>
              <span className="text-xs font-bold text-red-400 uppercase">Stop & Convert</span>
            </button>
          )}
        </div>

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

        {/* CROWDSOURCING LINK */}
        <div className="mt-6 text-center">
            <button 
              onClick={() => setShowModal(true)}
              className="text-xs text-gray-400 hover:text-cyan-400 transition-colors uppercase tracking-widest font-bold flex items-center justify-center mx-auto gap-2"
            >
              <FontAwesomeIcon icon={faPlusCircle} />
              Missing a factor? Suggest one here
            </button>
        </div>
      </div>

      {/* RESULTS DISPLAY */}
      {result && (
        <div className="mt-10 w-full max-w-2xl animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="bg-gray-800 p-8 rounded-2xl border-l-8 border-green-500 shadow-2xl">
            <h3 className="text-2xl font-bold text-white mb-4">Impact Summary</h3>
            <div className="flex flex-col items-center py-4">
              <span className="text-6xl font-black text-green-400">{result.total_co2e_kg}</span>
              <span className="text-xl font-medium text-gray-400 mt-2">kg CO₂e Total Impact</span>
            </div>
            {result.activities?.map((act, idx) => (
              <div key={idx} className="flex justify-between text-sm mt-3 border-t border-gray-700 pt-2">
                <span className="text-gray-300 capitalize">{act.activity_type}: {act.key}</span>
                <span className="text-green-500 font-mono font-bold">+{act.co2e} kg</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* FOOTER */}
      <div className="mt-12 flex space-x-6 text-sm">
        <Link to="/dashboard" className="text-gray-500 hover:text-white underline">Back to Dashboard</Link>
        <button onClick={() => {setResult(null); setActivityText("");}} className="text-gray-500 hover:text-red-400">Clear All</button>
      </div>

      {/* CROWDSOURCING MODAL */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
          <div className="bg-gray-800 rounded-2xl p-8 max-w-md w-full border border-gray-700 shadow-2xl">
            <h2 className="text-2xl font-bold mb-6 text-green-400">Suggest New Factor</h2>
            <form onSubmit={handleCustomFactorSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Category</label>
                <select 
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg p-3 text-white focus:ring-2 focus:ring-green-500"
                  value={customFactor.activity_type}
                  onChange={(e) => setCustomFactor({...customFactor, activity_type: e.target.value})}
                >
                  <option value="TRANSPORT">Transport</option>
                  <option value="FOOD">Food</option>
                  <option value="ENERGY">Energy/Utilities</option>
                </select>
              </div>
              <input 
                type="text" placeholder="Activity Name (e.g. Electric_Rickshaw)"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg p-3 text-white focus:ring-2 focus:ring-green-500"
                required value={customFactor.key}
                onChange={(e) => setCustomFactor({...customFactor, key: e.target.value})}
              />
              <div className="flex gap-2">
                <input 
                  type="number" step="0.0001" placeholder="CO2 Value"
                  className="flex-1 bg-gray-900 border border-gray-700 rounded-lg p-3 text-white focus:ring-2 focus:ring-green-500"
                  required value={customFactor.co2e_per_unit}
                  onChange={(e) => setCustomFactor({...customFactor, co2e_per_unit: e.target.value})}
                />
                <input 
                  type="text" placeholder="Unit"
                  className="w-24 bg-gray-900 border border-gray-700 rounded-lg p-3 text-white"
                  required value={customFactor.unit}
                  onChange={(e) => setCustomFactor({...customFactor, unit: e.target.value})}
                />
              </div>
              <textarea 
                placeholder="Source Link or Reference"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg p-3 text-white h-24 focus:ring-2 focus:ring-green-500"
                value={customFactor.source_reference}
                onChange={(e) => setCustomFactor({...customFactor, source_reference: e.target.value})}
              />
              <div className="flex justify-end gap-3 mt-8">
                <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-gray-400 hover:text-white">Cancel</button>
                <button type="submit" className="bg-green-600 hover:bg-green-500 text-white font-bold py-2 px-6 rounded-lg">
                  Submit for Review
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Activity;