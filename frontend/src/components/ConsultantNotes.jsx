import { useState } from "react";
import { consultantAPI, ocrAPI } from "../services/api";
import "./ConsultantNotes.css";

export default function ConsultantNotes({ selectedPatient }) {
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [structured, setStructured] = useState(null);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [editMode, setEditMode] = useState(false);
  const [pastNotes, setPastNotes] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [qualityReports, setQualityReports] = useState([]);
  const [regions, setRegions] = useState([]);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [tesseractResult, setTesseractResult] = useState(null);

  const handleFileChange = (e) => {
    const selected = Array.from(e.target.files);
    setFiles(selected);
    setPreviews(selected.map((f) => URL.createObjectURL(f)));
    setStructured(null);
    setTesseractResult(null);
    setError("");
    setQualityReports([]);
    setRegions([]);
  };

  const handleTesseractExtract = async () => {
    if (!files.length) return alert("Please select images first");

    setOcrLoading(true);
    setError("");

    try {
      const responses = await Promise.all(files.map((file) => ocrAPI.extract(file)));

      const extractedParts = responses
        .map((res) => {
          const text = (res?.extracted_text || "").trim();
          if (!text) return "";
          return files.length > 1
            ? `[${res.filename || "image"}]\n${text}`
            : text;
        })
        .filter(Boolean);

      const confidenceScores = responses
        .map((res) => Number(res?.confidence_score || 0))
        .filter((n) => !Number.isNaN(n));

      const avgConfidence = confidenceScores.length
        ? Math.round((confidenceScores.reduce((a, b) => a + b, 0) / confidenceScores.length) * 100) / 100
        : 0;

      const mergedMedicalFields = {};
      responses.forEach((res) => {
        const fields = res?.medical_fields || {};
        Object.keys(fields).forEach((key) => {
          if (!mergedMedicalFields[key]) {
            mergedMedicalFields[key] = fields[key];
          }
        });
      });

      setTesseractResult({
        text: extractedParts.join("\n\n"),
        confidence: avgConfidence,
        medicalFields: mergedMedicalFields,
      });
    } catch (err) {
      setError(err.response?.data?.error || err.message);
      setTesseractResult(null);
    } finally {
      setOcrLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!files.length) return alert("Please select images first");
    setExtracting(true);
    setError("");
    try {
      const res = await consultantAPI.extractNotes(files);
      setStructured(res.extracted_json);
      if (res.quality_reports) setQualityReports(res.quality_reports);
      if (res.regions) setRegions(res.regions);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setExtracting(false);
    }
  };

  const handleSave = async () => {
    if (!structured || !selectedPatient) return;
    setSaving(true);
    try {
      await consultantAPI.saveNotes(selectedPatient.name, structured);
      alert("Saved to EMR successfully!");
      setStructured(null);
      setFiles([]);
      setPreviews([]);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setSaving(false);
    }
  };

  const loadHistory = async () => {
    if (!selectedPatient) return;
    try {
      const res = await consultantAPI.getNotes(selectedPatient.name);
      setPastNotes(Array.isArray(res) ? res : []);
      setShowHistory(true);
    } catch {
      setPastNotes([]);
      setShowHistory(true);
    }
  };

  const renderStructuredData = (data) => {
    if (!data) return null;

    return (
      <div className="ocr-result">
        {/* Document Type Badge */}
        {data.document_type && (
          <div className="doc-type-badge">{data.document_type}</div>
        )}

        {/* Patient Info Card */}
        {data.patient_info && (
          <div className="ocr-card">
            <h4>Patient Information</h4>
            <div className="info-grid">
              {Object.entries(data.patient_info).map(
                ([key, val]) =>
                  val && (
                    <div key={key} className="info-item">
                      <span className="info-label">
                        {key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                      </span>
                      <span className="info-value">{val}</span>
                    </div>
                  )
              )}
            </div>
          </div>
        )}

        {/* Primary transcription output */}
        {data.transcribed_text && (
          <div className="ocr-card highlight-blue">
            <h4>Transcribed Text</h4>
            <div className="section-content">{data.transcribed_text}</div>
          </div>
        )}

        {/* Sections */}
        {data.sections?.length > 0 && (
          <div className="ocr-card">
            <h4>Document Sections</h4>
            {data.sections.map((sec, i) => (
              <div key={i} className="section-block">
                <div className="section-title">{sec.title}</div>
                <div className="section-content">{sec.content}</div>
              </div>
            ))}
          </div>
        )}

        {/* Fallback Transcription */}
        {(!data.sections?.length && data.notes) && (
          <div className="ocr-card">
            <h4>Transcribed Text</h4>
            <div className="section-content">{data.notes}</div>
          </div>
        )}

        {data.raw_text && (
          <div className="ocr-card">
            <h4>Raw OCR Text</h4>
            <div className="section-content">{data.raw_text}</div>
          </div>
        )}

        {/* Diagnosis */}
        {data.diagnosis && (
          <div className="ocr-card highlight-blue">
            <h4>Diagnosis</h4>
            <p>{data.diagnosis}</p>
          </div>
        )}

        {/* Investigations */}
        {data.investigations && (
          <div className="ocr-card">
            <h4>Investigations</h4>
            <p>{data.investigations}</p>
          </div>
        )}

        {/* Prescription */}
        {data.prescription && (
          <div className="ocr-card highlight-green">
            <h4>Prescription / Treatment</h4>
            <p>{data.prescription}</p>
          </div>
        )}

        {/* Notes */}
        {data.notes && (
          <div className="ocr-card">
            <h4>Additional Notes</h4>
            <p>{data.notes}</p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="doc-uploader-container">
      <div className="doc-header">
        <h2>Document Scanner</h2>
        <div className="header-actions">
          {selectedPatient && (
            <button className="history-btn" onClick={loadHistory}>
              View History
            </button>
          )}
          <span className="patient-id-pill">
            {selectedPatient?.name || "No patient"}
          </span>
        </div>
      </div>

      {!selectedPatient ? (
        <div className="no-patient">Select a patient first</div>
      ) : (
        <>
          {/* Upload Area */}
          <div className="upload-area">
            <input
              id="file-input"
              type="file"
              accept="image/*"
              multiple
              onChange={handleFileChange}
              className="file-input"
            />
            <label htmlFor="file-input" className="file-label">
              {files.length
                ? `${files.length} image(s) selected`
                : "Click to select images"}
            </label>
            <button
              className="primary-btn"
              onClick={handleUpload}
              disabled={!files.length || extracting}
            >
              {extracting ? "Extracting..." : "Upload & Extract"}
            </button>
            <button
              className="primary-btn"
              onClick={handleTesseractExtract}
              disabled={!files.length || ocrLoading}
            >
              {ocrLoading ? "Running OCR..." : "Run Tesseract OCR"}
            </button>
          </div>

          {/* Image Previews */}
          {previews.length > 0 && (
            <div className="preview-row">
              {previews.map((src, i) => (
                <img key={i} src={src} alt={`preview-${i}`} className="preview-thumb" />
              ))}
            </div>
          )}

          {/* Error */}
          {error && <div className="error-banner">{error}</div>}

          {/* Extraction Progress */}
          {extracting && (
            <div className="extracting-indicator">
              <div className="spinner" />
              <span>AI is reading the document...</span>
            </div>
          )}

          {ocrLoading && (
            <div className="extracting-indicator">
              <div className="spinner" />
              <span>Tesseract is extracting text...</span>
            </div>
          )}

          {tesseractResult && (
            <div className="results-section">
              <div className="results-header">
                <h3>Tesseract OCR</h3>
              </div>
              <div className="ocr-result">
                <div className="ocr-card highlight-blue">
                  <h4>Transcribed Text</h4>
                  <div className="section-content">
                    {tesseractResult.text || "No text extracted."}
                  </div>
                </div>
                <div className="ocr-card">
                  <h4>Confidence</h4>
                  <p>{tesseractResult.confidence}</p>
                </div>
                {Object.keys(tesseractResult.medicalFields || {}).length > 0 && (
                  <div className="ocr-card highlight-green">
                    <h4>Parsed Medical Fields</h4>
                    <div className="section-content">
                      {Object.entries(tesseractResult.medicalFields).map(([key, value]) => (
                        <div key={key}>
                          {key}: {value.value} {value.unit || ""}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Image Quality Reports */}
          {qualityReports.length > 0 && (
            <div className="quality-reports-section">
              <h3 className="quality-section-title">
                Image Quality Analysis
              </h3>
              {qualityReports.map((report, idx) => (
                <div key={idx} className={`quality-card quality-${report.quality_rating}`}>
                  <div className="quality-card-header">
                    <span className="quality-filename">{report.filename || `Image ${idx + 1}`}</span>
                    <div className="quality-score-pill">
                      <span className={`quality-dot ${report.quality_rating}`} />
                      {report.overall_score}/100 — {report.quality_rating}
                    </div>
                  </div>
                  <div className="quality-metrics">
                    <div className="quality-metric">
                      <span className="metric-label">Sharpness</span>
                      <div className="metric-bar-track">
                        <div
                          className={`metric-bar-fill ${report.blur?.label}`}
                          style={{ width: `${report.blur?.score || 0}%` }}
                        />
                      </div>
                      <span className="metric-value">{report.blur?.label}</span>
                    </div>
                    <div className="quality-metric">
                      <span className="metric-label">Contrast</span>
                      <div className="metric-bar-track">
                        <div
                          className={`metric-bar-fill ${report.contrast?.label}`}
                          style={{ width: `${report.contrast?.score || 0}%` }}
                        />
                      </div>
                      <span className="metric-value">{report.contrast?.label}</span>
                    </div>
                    <div className="quality-metric">
                      <span className="metric-label">Brightness</span>
                      <div className="metric-bar-track">
                        <div
                          className={`metric-bar-fill ${report.brightness?.label === 'good' ? 'good' : 'low'}`}
                          style={{ width: `${report.brightness?.score || 0}%` }}
                        />
                      </div>
                      <span className="metric-value">{report.brightness?.label}</span>
                    </div>
                    <div className="quality-metric">
                      <span className="metric-label">Resolution</span>
                      <div className="metric-bar-track">
                        <div
                          className="metric-bar-fill good"
                          style={{ width: `${report.resolution?.score || 0}%` }}
                        />
                      </div>
                      <span className="metric-value">{report.resolution?.rating}</span>
                    </div>
                  </div>
                  {report.issues?.length > 0 && (
                    <div className="quality-issues">
                      {report.issues.map((issue, i) => (
                        <div key={i} className="quality-issue">{issue}</div>
                      ))}
                    </div>
                  )}
                  {report.recommendations?.length > 0 && (
                    <div className="quality-recommendations">
                      {report.recommendations.map((rec, i) => (
                        <div key={i} className="quality-rec">{rec}</div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Results */}
          {structured && (
            <div className="results-section">
              <div className="results-header">
                <h3>Extracted Data</h3>
                <button
                  className="toggle-btn"
                  onClick={() => setEditMode(!editMode)}
                >
                  {editMode ? "Structured View" : "Edit JSON"}
                </button>
              </div>

              {editMode ? (
                <textarea
                  className="json-editor"
                  value={JSON.stringify(structured, null, 2)}
                  onChange={(e) => {
                    try {
                      setStructured(JSON.parse(e.target.value));
                    } catch {
                      /* ignore invalid JSON while typing */
                    }
                  }}
                />
              ) : (
                renderStructuredData(structured)
              )}

              <button
                className="save-btn"
                disabled={saving}
                onClick={handleSave}
              >
                {saving ? "Saving..." : "Save to Patient Record"}
              </button>
            </div>
          )}

          {/* History Panel */}
          {showHistory && (
            <div className="history-panel">
              <div className="history-header">
                <h3>Past Extracted Documents</h3>
                <button className="close-btn" onClick={() => setShowHistory(false)}>
                  Close
                </button>
              </div>
              {pastNotes.length === 0 ? (
                <p className="empty-history">No previous documents found.</p>
              ) : (
                pastNotes.map((note, idx) => (
                  <div key={idx} className="history-item">
                    <div className="history-meta">
                      Uploaded: {new Date(note.uploaded_at).toLocaleString()}
                    </div>
                    {renderStructuredData(note.data)}
                  </div>
                ))
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
