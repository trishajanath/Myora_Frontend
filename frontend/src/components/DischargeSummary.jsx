import { useState } from "react";
import "./DischargeSummary.css";
import { dischargeAPI } from "../services/api";

function DischargeSummary({ selectedPatient }) {
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [approving, setApproving] = useState(false);
  const [approved, setApproved] = useState(false);
  const [editingNarrative, setEditingNarrative] = useState(false);
  const [narrativeText, setNarrativeText] = useState("");

  const generateSummary = async () => {
    if (!selectedPatient) return;
    setLoading(true);
    setError("");
    setSummary(null);
    setApproved(false);

    try {
      const result = await dischargeAPI.generate({
        patient_id: selectedPatient.name,
        patient_name: selectedPatient.name,
        patient_age: selectedPatient.age ? String(selectedPatient.age) : "",
      });

      if (result.success) {
        setSummary(result.discharge_summary);
        setNarrativeText(result.discharge_summary.narrative_summary || "");
      } else {
        setError(result.error || "Failed to generate summary");
      }
    } catch (err) {
      const msg = err.response?.data?.error || err.message;
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const approveSummary = async () => {
    if (!summary || !selectedPatient) return;
    setApproving(true);

    try {
      const finalSummary = { ...summary, narrative_summary: narrativeText };
      const result = await dischargeAPI.approve({
        patient_id: selectedPatient.name,
        patient_name: selectedPatient.name,
        summary: finalSummary,
      });

      if (result.success) {
        setApproved(true);
      } else {
        setError(result.error || "Approval failed");
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setApproving(false);
    }
  };

  if (!selectedPatient) {
    return (
      <div className="discharge-container">
        <div className="discharge-empty">
          <h3>No Patient Selected</h3>
          <p>Select a patient from the list to generate a discharge summary</p>
        </div>
      </div>
    );
  }

  return (
    <div className="discharge-container">
      <div className="discharge-header">
        <div>
          <h2>Discharge Summary</h2>
          <p className="discharge-subtitle">
            Compile all visit records into a formatted discharge summary
          </p>
        </div>
        <span className="patient-badge">{selectedPatient.name}</span>
      </div>

      {!summary && !loading && (
        <div className="discharge-generate-section">
          <p>
            This will pull all EMR voice notes, consultant notes, diagnoses,
            medications, and advice into a formatted discharge summary for
            review and approval.
          </p>
          <button onClick={generateSummary} className="generate-discharge-btn">
            Generate Discharge Summary
          </button>
        </div>
      )}

      {loading && (
        <div className="discharge-loading">
          <div className="discharge-spinner" />
          <p>Compiling patient records and generating summary...</p>
        </div>
      )}

      {error && (
        <div className="discharge-error">
          <strong>Error:</strong> {error}
          <button onClick={() => setError("")} className="dismiss-btn">
            Dismiss
          </button>
        </div>
      )}

      {summary && (
        <div className="discharge-content">
          {/* Overview Cards */}
          <div className="discharge-overview">
            <div className="overview-card">
              <span className="overview-label">Patient</span>
              <span className="overview-value">{summary.patient_name}</span>
            </div>
            {summary.patient_age && (
              <div className="overview-card">
                <span className="overview-label">Age</span>
                <span className="overview-value">{summary.patient_age}</span>
              </div>
            )}
            <div className="overview-card">
              <span className="overview-label">Admission</span>
              <span className="overview-value">
                {summary.admission_date || "N/A"}
              </span>
            </div>
            <div className="overview-card">
              <span className="overview-label">Discharge</span>
              <span className="overview-value">{summary.discharge_date}</span>
            </div>
            <div className="overview-card">
              <span className="overview-label">Total Visits</span>
              <span className="overview-value">{summary.total_visits}</span>
            </div>
          </div>

          {/* Diagnoses */}
          {summary.diagnoses && summary.diagnoses.length > 0 && (
            <div className="discharge-section">
              <h3>Diagnoses</h3>
              <ul className="discharge-list">
                {summary.diagnoses.map((dx, i) => (
                  <li key={i}>{dx}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Allergies */}
          {summary.allergies && summary.allergies.length > 0 && (
            <div className="discharge-section">
              <h3>Allergies</h3>
              <div className="allergy-tags">
                {summary.allergies.map((a, i) => (
                  <span key={i} className="allergy-tag">{a}</span>
                ))}
              </div>
            </div>
          )}

          {/* Medications at Discharge */}
          {summary.medications_at_discharge &&
            summary.medications_at_discharge.length > 0 && (
              <div className="discharge-section">
                <h3>Medications at Discharge</h3>
                <table className="discharge-med-table">
                  <thead>
                    <tr>
                      <th>Medication</th>
                      <th>Dosage</th>
                      <th>Frequency</th>
                      <th>Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.medications_at_discharge.map((med, i) => (
                      <tr key={i}>
                        <td>
                          {typeof med === "string"
                            ? med
                            : med.Medication || med.medication || ""}
                        </td>
                        <td>{med.Dosage || med.dosage || "-"}</td>
                        <td>{med.Frequency || med.frequency || "-"}</td>
                        <td>{med.Duration || med.duration || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

          {/* Advice / Follow-Up */}
          {summary.advice_followup && summary.advice_followup.length > 0 && (
            <div className="discharge-section">
              <h3>Advice / Follow-Up</h3>
              <ul className="discharge-list">
                {summary.advice_followup.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Narrative Summary */}
          <div className="discharge-section narrative-section">
            <div className="narrative-header">
              <h3>Narrative Summary</h3>
              <button
                onClick={() => setEditingNarrative(!editingNarrative)}
                className="edit-narrative-btn"
              >
                {editingNarrative ? "Preview" : "Edit"}
              </button>
            </div>
            {editingNarrative ? (
              <textarea
                className="narrative-editor"
                value={narrativeText}
                onChange={(e) => setNarrativeText(e.target.value)}
                rows={8}
              />
            ) : (
              <div className="narrative-text">{narrativeText}</div>
            )}
          </div>

          {/* Approve / Regenerate Actions */}
          {approved ? (
            <div className="discharge-approved-banner">
              Discharge summary approved and saved
            </div>
          ) : (
            <div className="discharge-actions">
              <button
                onClick={approveSummary}
                disabled={approving}
                className="approve-btn"
              >
                {approving ? "Saving..." : "Approve and Save"}
              </button>
              <button
                onClick={generateSummary}
                disabled={loading}
                className="regenerate-btn"
              >
                Regenerate
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default DischargeSummary;
