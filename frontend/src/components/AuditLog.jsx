import { useState, useEffect, useCallback } from "react";
import { auditAPI } from "../services/api";
import "./AuditLog.css";

const ACTION_LABELS = {
  PATIENT_VIEW: "View Patient",
  PATIENT_VIEW_ALL: "View All Patients",
  PATIENT_CREATE: "Create Patient",
  PATIENT_UPDATE: "Update Patient",
  PATIENT_DELETE: "Delete Patient",
  VOICE_TRANSCRIBE: "Voice Transcription",
  VOICE_PROCESS: "AI Processing",
  EMR_SAVE: "Save EMR Record",
  EMR_VIEW_HISTORY: "View EMR History",
  OCR_EXTRACT: "Document OCR Extract",
  OCR_SAVE: "Save OCR Document",
  OCR_VIEW: "View OCR Documents",
};

const ACTION_COLORS = {
  PATIENT_VIEW: "#374151",
  PATIENT_VIEW_ALL: "#374151",
  PATIENT_CREATE: "#111827",
  PATIENT_UPDATE: "#6b7280",
  PATIENT_DELETE: "#dc2626",
  VOICE_TRANSCRIBE: "#4b5563",
  VOICE_PROCESS: "#4b5563",
  EMR_SAVE: "#111827",
  EMR_VIEW_HISTORY: "#374151",
  OCR_EXTRACT: "#6b7280",
  OCR_SAVE: "#111827",
  OCR_VIEW: "#374151",
};

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterAction, setFilterAction] = useState("");
  const [filterPatient, setFilterPatient] = useState("");
  const [limit, setLimit] = useState(100);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await auditAPI.getLogs({
        action: filterAction || undefined,
        patientId: filterPatient || undefined,
        limit,
      });
      setLogs(res.logs || []);
    } catch (err) {
      console.error("Failed to fetch audit logs:", err);
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [filterAction, filterPatient, limit]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const formatDate = (iso) => {
    const d = new Date(iso);
    return d.toLocaleString();
  };

  const uniqueActions = Object.keys(ACTION_LABELS);

  return (
    <div className="audit-container">
      <div className="audit-header">
        <div>
          <h2>HIPAA Audit Log</h2>
          <p className="audit-subtitle">
            All access to Protected Health Information is logged here
          </p>
        </div>
        <button className="refresh-btn" onClick={fetchLogs} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {/* Filters */}
      <div className="audit-filters">
        <div className="filter-group">
          <label>Action Type</label>
          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
          >
            <option value="">All Actions</option>
            {uniqueActions.map((a) => (
              <option key={a} value={a}>
                {ACTION_LABELS[a]}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Patient ID</label>
          <input
            type="text"
            placeholder="Filter by patient..."
            value={filterPatient}
            onChange={(e) => setFilterPatient(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label>Limit</label>
          <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500</option>
          </select>
        </div>
      </div>

      {/* Stats bar */}
      <div className="audit-stats">
        <span>{logs.length} entries loaded</span>
      </div>

      {/* Log Table */}
      {loading ? (
        <div className="audit-loading">
          <div className="spinner" />
          Loading audit trail...
        </div>
      ) : logs.length === 0 ? (
        <div className="audit-empty">No audit logs found for the current filters.</div>
      ) : (
        <div className="audit-table-wrapper">
          <table className="audit-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Patient</th>
                <th>User</th>
                <th>IP Address</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log, idx) => (
                <tr key={idx}>
                  <td className="td-time">{formatDate(log.timestamp)}</td>
                  <td>
                    <span
                      className="action-badge"
                      style={{ background: ACTION_COLORS[log.action] || "#6b7280" }}
                    >
                      {ACTION_LABELS[log.action] || log.action}
                    </span>
                  </td>
                  <td className="td-patient">{log.patient_id || "-"}</td>
                  <td>{log.user || "system"}</td>
                  <td className="td-ip">{log.ip_address || "-"}</td>
                  <td className="td-details">
                    {log.details && Object.keys(log.details).length > 0 ? (
                      <span className="details-text">
                        {Object.entries(log.details)
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(", ")}
                      </span>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
