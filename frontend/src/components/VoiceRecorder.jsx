import { useState, useRef } from "react";

function VoiceRecorder({ selectedPatient, onNoteSaved }) {
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState("Ready to record");
  const [transcription, setTranscription] = useState("");
  const [structuredData, setStructuredData] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [confidence, setConfidence] = useState(0);
  const [debugLogs, setDebugLogs] = useState([]);
  const [editMode, setEditMode] = useState(false);
  const [editedData, setEditedData] = useState(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [recordingTime, setRecordingTime] = useState(0);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);
  const timerRef = useRef(null);

  const API_BASE = "http://localhost:5000";

  const addLog = (message, type = "info") => {
    const timestamp = new Date().toLocaleTimeString();
    setDebugLogs(prev => [...prev.slice(-30), { timestamp, message, type }]);
    console.log(`[${timestamp}] ${message}`);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const startRecording = async () => {
    if (!selectedPatient) {
      alert("Please select a patient first");
      return;
    }

    try {
      setIsRecording(true);
      setTranscription("");
      setStructuredData(null);
      setEditMode(false);
      setConfidence(0);
      setRecordingTime(0);
      audioChunksRef.current = [];
      
      addLog(`🎙️ Starting recording for ${selectedPatient.name}`, "success");
      setStatus("🎤 Recording... Click STOP when finished");

      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1
        }
      });
      streamRef.current = stream;
      addLog("✅ Microphone access granted", "success");

      // Setup audio level monitoring
      const audioContext = new AudioContext();
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateLevel = () => {
        if (!streamRef.current) return;
        analyser.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        setAudioLevel(Math.min(100, average * 1.5));
        requestAnimationFrame(updateLevel);
      };
      updateLevel();

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

      // Setup MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
          addLog(`📦 Audio chunk collected (${audioChunksRef.current.length})`, "info");
        }
      };

      mediaRecorder.onstop = async () => {
        addLog("🛑 Recording stopped, processing...", "info");
        await processAudioChunks();
      };

      // Start recording
      mediaRecorder.start(1000); // Collect data every second
      addLog("🎤 Recording started - speak your notes now!", "success");

    } catch (err) {
      addLog(`❌ Error: ${err.message}`, "error");
      setStatus(`⚠️ Error: ${err.message}`);
      setIsRecording(false);
      cleanupAudio();
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      addLog("⏹️ Stopping recording...", "info");
    }
    setIsRecording(false);
    setStatus("⏳ Processing audio...");
    cleanupAudio();
  };

  const cleanupAudio = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  };

  const processAudioChunks = async () => {
    if (audioChunksRef.current.length === 0) {
      setStatus("❌ No audio recorded");
      addLog("No audio chunks collected", "error");
      setIsProcessing(false);
      return;
    }

    setIsProcessing(true);
    setStatus("🔄 Transcribing with Deepgram...");
    addLog(`📤 Sending ${audioChunksRef.current.length} audio chunks to backend`, "info");

    try {
      // Create audio blob
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      const sizeKB = (audioBlob.size / 1024).toFixed(2);
      addLog(`📦 Audio size: ${sizeKB} KB`, "info");

      // Send to backend for transcription
      const formData = new FormData();
      formData.append('audio_data', audioBlob, 'recording.webm');
      formData.append('patient_id', selectedPatient.name);

      addLog("🌐 Calling Deepgram API...", "info");
      const response = await fetch(`${API_BASE}/api/voice/transcribe`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.error || "Transcription failed");
      }

      const transcript = result.transcript.trim();
      const conf = result.confidence || 0;
      
      addLog(`✅ Transcription complete!`, "success");
      addLog(`📊 Confidence: ${(conf * 100).toFixed(1)}%`, "success");
      addLog(`📝 Length: ${transcript.length} characters`, "info");
      
      setTranscription(transcript);
      setConfidence(conf);
      setStatus("✅ Transcription complete! Processing with AI...");

      // Immediately process with Gemini
      await processWithGemini(transcript);

    } catch (err) {
      addLog(`❌ Error: ${err.message}`, "error");
      setStatus(`⚠️ Error: ${err.message}`);
      setIsProcessing(false);
    }
  };

  const processWithGemini = async (notes) => {
    if (!notes || notes.trim().length < 10) {
      setStatus("⚠️ Transcript too short to process");
      setIsProcessing(false);
      return;
    }

    setStatus("🤖 Structuring data with AI...");
    addLog(`🤖 Processing ${notes.length} chars with Gemini`, "info");

    try {
      const response = await fetch(`${API_BASE}/api/voice/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: selectedPatient.name,
          notes: notes.trim()
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.error || "Processing failed");
      }

      setStructuredData(result.structured);
      setEditedData(result.structured);
      setStatus("✅ EMR data ready! Review and save.");
      addLog("✅ Structured data generated", "success");
    } catch (err) {
      addLog(`❌ AI Error: ${err.message}`, "error");
      setStatus(`⚠️ AI Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFieldEdit = (field, value) => {
    setEditedData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const saveToDatabase = async () => {
    if (!editedData || !selectedPatient) return;
    
    setStatus("💾 Saving to database...");
    addLog("💾 Saving to MongoDB...", "info");

    try {
      const response = await fetch(`${API_BASE}/api/voice/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: selectedPatient.name,
          raw_notes: transcription,
          structured: editedData,
          confidence: confidence
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const result = await response.json();
      setStatus("✅ Saved successfully!");
      addLog(`✅ Saved! ID: ${result.id}`, "success");
      
      // Clear form
      setTranscription("");
      setStructuredData(null);
      setEditedData(null);
      setEditMode(false);
      setConfidence(0);
      setRecordingTime(0);
      
      onNoteSaved?.();
    } catch (err) {
      addLog(`❌ Save error: ${err.message}`, "error");
      setStatus(`⚠️ Save error: ${err.message}`);
    }
  };

  const testConnection = async () => {
    addLog("🧪 Testing backend connection...", "info");
    try {
      const response = await fetch(`${API_BASE}/health`);
      const data = await response.json();
      addLog(`✅ Backend: ${data.status}, DB: ${data.database}, Deepgram: ${data.deepgram}`, "success");
      setStatus("✅ Backend connection OK");
    } catch (err) {
      addLog(`❌ Backend not responding: ${err.message}`, "error");
      setStatus("❌ Cannot connect to backend");
    }
  };

  return (
    <div style={{ padding: "20px", fontFamily: "system-ui", maxWidth: "1200px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", padding: "20px", borderRadius: "12px", marginBottom: "20px", color: "white" }}>
        <h2 style={{ margin: "0 0 10px 0" }}>Voice Medical Notes</h2>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
          {selectedPatient ? (
            <span style={{ background: "rgba(255,255,255,0.2)", padding: "5px 15px", borderRadius: "20px", fontSize: "14px" }}>
              👤 Patient: {selectedPatient.name}
            </span>
          ) : (
            <span style={{ background: "rgba(255,255,255,0.2)", padding: "5px 15px", borderRadius: "20px", fontSize: "14px" }}>
              ⚠️ No patient selected
            </span>
          )}
          <div style={{ display: "flex", gap: "10px" }}>
            <span style={{ background: "rgba(33, 150, 243, 0.3)", padding: "5px 15px", borderRadius: "20px", fontSize: "12px" }}>
              Deepgram Medical
            </span>
          </div>
        </div>
      </div>

      {!selectedPatient ? (
        <div style={{ textAlign: "center", padding: "60px 20px", background: "#f8f9fa", borderRadius: "12px", border: "2px dashed #ddd" }}>
          <div style={{ fontSize: "48px", marginBottom: "20px" }}>🏥</div>
          <h3 style={{ color: "#666", marginBottom: "10px" }}>No Patient Selected</h3>
          <p style={{ color: "#999", fontSize: "16px" }}>Please select a patient to start voice dictation</p>
        </div>
      ) : (
        <>
          {/* Controls */}
          <div style={{ marginBottom: "20px", display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isProcessing}
              style={{
                padding: "15px 40px",
                fontSize: "18px",
                borderRadius: "25px",
                border: "none",
                background: isRecording ? "#e74c3c" : "#27ae60",
                color: "white",
                cursor: isProcessing ? "not-allowed" : "pointer",
                opacity: isProcessing ? 0.5 : 1,
                transition: "all 0.3s",
                boxShadow: "0 4px 6px rgba(0,0,0,0.1)",
                fontWeight: "600"
              }}
            >
              {isRecording ? " Stop Recording" : " Start Recording"}
            </button>

            {/* Recording Timer */}
            {isRecording && (
              <div style={{
                padding: "10px 20px",
                background: "#e74c3c",
                color: "white",
                borderRadius: "20px",
                fontWeight: "600",
                fontSize: "16px",
                display: "flex",
                alignItems: "center",
                gap: "8px"
              }}>
                <div style={{
                  width: "12px",
                  height: "12px",
                  background: "white",
                  borderRadius: "50%",
                  animation: "pulse 1.5s infinite"
                }} />
                {formatTime(recordingTime)}
              </div>
            )}

            {confidence > 0 && (
              <div style={{ 
                padding: "10px 20px", 
                background: confidence > 0.9 ? "#d4edda" : confidence > 0.7 ? "#fff3cd" : "#f8d7da",
                borderRadius: "20px",
                fontSize: "14px",
                fontWeight: "600",
                color: "#333"
              }}>
                📊 Confidence: {(confidence * 100).toFixed(1)}%
              </div>
            )}
          </div>

          {/* Audio Level Indicator */}
          {isRecording && (
            <div style={{ marginBottom: "20px", padding: "15px", background: "#f8f9fa", borderRadius: "8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ fontSize: "14px", color: "#666", fontWeight: "600" }}>🔊 Audio Level</span>
                <span style={{ fontSize: "14px", color: "#666" }}>
                  {audioLevel > 80 ? "🔴 Too Loud" : audioLevel > 20 ? "🟢 Good" : "🟡 Too Quiet"}
                </span>
              </div>
              <div style={{ background: "#ddd", height: "12px", borderRadius: "6px", overflow: "hidden" }}>
                <div style={{ 
                  background: audioLevel > 80 ? "#e74c3c" : audioLevel > 20 ? "#27ae60" : "#f39c12",
                  height: "100%", 
                  width: `${Math.min(100, audioLevel)}%`, 
                  transition: "width 0.1s, background 0.3s",
                  borderRadius: "6px"
                }} />
              </div>
            </div>
          )}

          {/* Status Bar */}
          <div style={{ 
            padding: "15px 20px", 
            background: isProcessing ? "#fff3cd" : structuredData ? "#d4edda" : isRecording ? "#e3f2fd" : "#f8f9fa",
            borderLeft: `4px solid ${isProcessing ? "#ffc107" : structuredData ? "#28a745" : isRecording ? "#2196f3" : "#ccc"}`,
            borderRadius: "8px", 
            marginBottom: "20px",
            fontSize: "15px",
            fontWeight: "500"
          }}>
            {status}
          </div>

          {/* Transcription */}
          {transcription && (
            <div style={{ 
              background: "white", 
              border: "2px solid #3498db", 
              borderRadius: "12px", 
              padding: "25px", 
              marginBottom: "20px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.1)"
            }}>
              <h3 style={{ margin: "0 0 15px 0", color: "#333", display: "flex", alignItems: "center", gap: "10px" }}>
                <span></span>
                <span>Transcription</span>
                <span style={{ fontSize: "14px", color: "#999", fontWeight: "normal" }}>
                  ({transcription.length} characters)
                </span>
              </h3>
              <div style={{ 
                background: "#f8f9fa",
                padding: "20px",
                borderRadius: "8px",
                whiteSpace: "pre-wrap", 
                lineHeight: "1.8",
                fontSize: "15px",
                color: "#333",
                minHeight: "80px",
                maxHeight: "300px",
                overflow: "auto"
              }}>
                {transcription}
              </div>
            </div>
          )}

          {/* Structured Data */}
          {structuredData && (
            <div style={{ 
              background: "white", 
              border: "2px solid #4CAF50", 
              borderRadius: "12px", 
              padding: "25px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.1)"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
                <h3 style={{ margin: 0, color: "#333", display: "flex", alignItems: "center", gap: "10px" }}>
                  <span>Structured EMR Data</span>
                </h3>
                <button
                  onClick={() => setEditMode(!editMode)}
                  style={{
                    padding: "8px 20px",
                    background: editMode ? "#6c757d" : "#007bff",
                    color: "white",
                    border: "none",
                    borderRadius: "20px",
                    cursor: "pointer",
                    fontSize: "14px",
                    fontWeight: "600",
                    transition: "all 0.3s"
                  }}
                >
                  {editMode ? " View Mode" : "Edit Mode"}
                </button>
              </div>

              {editMode ? (
                <div style={{ display: "grid", gap: "20px" }}>
                  {Object.entries(editedData).map(([key, value]) => (
                    <div key={key}>
                      <label style={{ 
                        display: "block", 
                        fontWeight: "600", 
                        marginBottom: "8px", 
                        color: "#555",
                        fontSize: "14px"
                      }}>
                        {key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
                      </label>
                      <textarea
                        value={Array.isArray(value) ? value.join(", ") : value}
                        onChange={(e) => handleFieldEdit(key, e.target.value)}
                        style={{
                          width: "100%",
                          padding: "12px",
                          borderRadius: "8px",
                          border: "2px solid #e0e0e0",
                          fontSize: "14px",
                          fontFamily: "inherit",
                          minHeight: "80px",
                          resize: "vertical",
                          transition: "border 0.3s"
                        }}
                        onFocus={(e) => e.target.style.border = "2px solid #007bff"}
                        onBlur={(e) => e.target.style.border = "2px solid #e0e0e0"}
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <pre style={{ 
                  background: "#f8f9fa", 
                  padding: "20px", 
                  borderRadius: "8px", 
                  overflow: "auto",
                  fontSize: "13px",
                  lineHeight: "1.6",
                  maxHeight: "150px"
                }}>
                  {JSON.stringify(structuredData, null, 2)}
                </pre>
              )}

              <button
                onClick={saveToDatabase}
                style={{
                  marginTop: "20px",
                  padding: "15px 40px",
                  background: "#28a745",
                  color: "white",
                  border: "none",
                  borderRadius: "25px",
                  cursor: "pointer",
                  fontSize: "16px",
                  fontWeight: "600",
                  boxShadow: "0 4px 6px rgba(0,0,0,0.2)",
                  transition: "all 0.3s",
                  width: "100%"
                }}
                onMouseOver={(e) => e.target.style.background = "#218838"}
                onMouseOut={(e) => e.target.style.background = "#28a745"}
              >
                 Save to Patient Record
              </button>
            </div>
          )}
        </>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.95); }
        }
      `}</style>
    </div>
  );
}

export default VoiceRecorder;



