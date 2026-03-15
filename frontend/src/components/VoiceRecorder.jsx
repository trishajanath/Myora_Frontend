import { useState, useRef } from "react";
import "./VoiceRecorder.css";

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

  const API_BASE = "http://localhost:5001";

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
      
      addLog(`Starting recording for ${selectedPatient.name}`, "success");
      setStatus("Recording... Click STOP when finished");

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
      addLog("Microphone access granted", "success");

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
          addLog(`Audio chunk collected (${audioChunksRef.current.length})`, "info");
        }
      };

      mediaRecorder.onstop = async () => {
        addLog("Recording stopped, processing...", "info");
        await processAudioChunks();
      };

      // Start recording
      mediaRecorder.start(1000); // Collect data every second
      addLog("Recording started - speak your notes now!", "success");

    } catch (err) {
      addLog(`Error: ${err.message}`, "error");
      setStatus(`Error: ${err.message}`);
      setIsRecording(false);
      cleanupAudio();
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      addLog("Stopping recording...", "info");
    }
    setIsRecording(false);
    setStatus("Processing audio...");
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
      setStatus("No audio recorded");
      addLog("No audio chunks collected", "error");
      setIsProcessing(false);
      return;
    }

    setIsProcessing(true);
    setStatus("Transcribing with Deepgram...");
    addLog(`Sending ${audioChunksRef.current.length} audio chunks to backend`, "info");

    try {
      // Create audio blob
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      const sizeKB = (audioBlob.size / 1024).toFixed(2);
      addLog(`Audio size: ${sizeKB} KB`, "info");

      // Send to backend for transcription
      const formData = new FormData();
      formData.append('audio_data', audioBlob, 'recording.webm');
      formData.append('patient_id', selectedPatient.name);

      addLog("Calling Deepgram API...", "info");
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
      
      addLog(`Transcription complete!`, "success");
      addLog(`Confidence: ${(conf * 100).toFixed(1)}%`, "success");
      addLog(`Length: ${transcript.length} characters`, "info");
      
      setTranscription(transcript);
      setConfidence(conf);
      setStatus("Transcription complete! Processing with AI...");

      // Immediately process with Gemini
      await processWithGemini(transcript);

    } catch (err) {
      addLog(`Error: ${err.message}`, "error");
      setStatus(`Error: ${err.message}`);
      setIsProcessing(false);
    }
  };

  const processWithGemini = async (notes) => {
    if (!notes || notes.trim().length < 10) {
      setStatus("Transcript too short to process");
      setIsProcessing(false);
      return;
    }

    setStatus("Structuring data with AI...");
    addLog(`Processing ${notes.length} chars with Gemini`, "info");

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
      setStatus("EMR data ready! Review and save.");
      addLog("Structured data generated", "success");
    } catch (err) {
      addLog(`AI Error: ${err.message}`, "error");
      setStatus(`AI Error: ${err.message}`);
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
    
    setStatus("Saving to database...");
    addLog("Saving to MongoDB...", "info");

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
      setStatus("Saved successfully!");
      addLog(`Saved! ID: ${result.id}`, "success");
      
      // Clear form
      setTranscription("");
      setStructuredData(null);
      setEditedData(null);
      setEditMode(false);
      setConfidence(0);
      setRecordingTime(0);
      
      onNoteSaved?.();
    } catch (err) {
      addLog(`Save error: ${err.message}`, "error");
      setStatus(`Save error: ${err.message}`);
    }
  };

  const testConnection = async () => {
    addLog("Testing backend connection...", "info");
    try {
      const response = await fetch(`${API_BASE}/health`);
      const data = await response.json();
      addLog(`Backend: ${data.status}, DB: ${data.database}, Deepgram: ${data.deepgram}`, "success");
      setStatus("Backend connection OK");
    } catch (err) {
      addLog(`Backend not responding: ${err.message}`, "error");
      setStatus("Cannot connect to backend");
    }
  };

  return (
    <div className="voice-recorder-container">
      {/* Header */}
      <div className="recorder-header">
        <div>
          <h2>Voice Medical Notes</h2>
          <p className="recorder-subtitle">Dictate clinical notes with AI-powered transcription</p>
        </div>
        <div className="recorder-header-right">
          {selectedPatient ? (
            <span className="patient-badge">{selectedPatient.name}</span>
          ) : (
            <span className="patient-badge-empty">No Patient</span>
          )}
          <span className="engine-badge">Deepgram Medical</span>
        </div>
      </div>

      {!selectedPatient ? (
        <div className="no-patient-selected">
          <div className="empty-icon"></div>
          <h3>No Patient Selected</h3>
          <p>Select a patient from the list to begin voice dictation</p>
        </div>
      ) : (
        <>
          {/* Controls */}
          <div className="recorder-controls-bar">
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isProcessing}
              className={`record-btn ${isRecording ? 'recording' : ''}`}
            >
              {isRecording ? (
                <><span className="pulse-dot" /> Stop Recording</>
              ) : (
                <>Start Recording</>
              )}
            </button>

            {isRecording && (
              <div className="recording-timer">
                <span className="timer-dot" />
                {formatTime(recordingTime)}
              </div>
            )}

            {confidence > 0 && (
              <div className={`confidence-pill ${confidence > 0.9 ? 'high' : confidence > 0.7 ? 'medium' : 'low'}`}>
                {(confidence * 100).toFixed(1)}% Confidence
              </div>
            )}
          </div>

          {/* Audio Level */}
          {isRecording && (
            <div className="audio-level-section">
              <div className="audio-level-header">
                <span className="audio-level-label">Audio Level</span>
                <span className="audio-level-status">
                  {audioLevel > 80 ? 'Too Loud' : audioLevel > 20 ? 'Good' : 'Too Quiet'}
                </span>
              </div>
              <div className="audio-level-track">
                <div
                  className={`audio-level-fill ${audioLevel > 80 ? 'loud' : audioLevel > 20 ? 'good' : 'quiet'}`}
                  style={{ width: `${Math.min(100, audioLevel)}%` }}
                />
              </div>
            </div>
          )}

          {/* Status */}
          <div className={`status-bar ${isProcessing ? 'processing' : structuredData ? 'success' : isRecording ? 'active' : ''}`}>
            <span className="status-text">{status}</span>
          </div>

          {/* Transcription */}
          {transcription && (
            <div className="transcription-section">
              <div className="section-header">
                <h3>Transcription</h3>
                <span className="char-count">{transcription.length} characters</span>
              </div>
              <div className="transcription-content">
                {transcription}
              </div>
            </div>
          )}

          {/* Structured Data */}
          {structuredData && (
            <div className="structured-section">
              <div className="section-header">
                <h3>Structured EMR Data</h3>
                <button
                  onClick={() => setEditMode(!editMode)}
                  className="toggle-mode-btn"
                >
                  {editMode ? 'View Mode' : 'Edit Mode'}
                </button>
              </div>

              {editMode ? (
                <div className="edit-fields">
                  {Object.entries(editedData).map(([key, value]) => (
                    <div key={key} className="edit-field-group">
                      <label>{key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}</label>
                      <textarea
                        value={Array.isArray(value) ? value.join(", ") : value}
                        onChange={(e) => handleFieldEdit(key, e.target.value)}
                        rows={3}
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <pre className="structured-preview">
                  {JSON.stringify(structuredData, null, 2)}
                </pre>
              )}

              <button onClick={saveToDatabase} className="save-record-btn">
                Save to Patient Record
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default VoiceRecorder;



