import { useState } from "react";
import axios from "axios";
import "./ConsultantNotes.css";

export default function ConsultantNotes({ selectedPatient }) {
  console.log("SELECTED PATIENT OBJECT:", selectedPatient) 
  const [files, setFiles] = useState([]);
  const [structured, setStructured] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleUpload = async () => {
    if (!files.length) return alert("Please select images first");

    const formData = new FormData();
    files.forEach((f) => formData.append("files", f)); // ✅ only files

    const res = await axios.post(
      "http://localhost:5000/api/consultant/extract_notes",
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      }
    );

    setStructured(res.data.extracted_json);
  };

  const handleSave = async () => {
    if (!structured) return;

    setSaving(true);

    await axios.post("http://localhost:5000/api/consultant/save_notes", {
      patient_id: selectedPatient.id,    // ✅ store correctly
      extracted_json: structured,                 // ✅ rename key
    });

    alert("Saved to DB ✅");
    setSaving(false);
    setStructured(null);
    setFiles([]);
  };
  

  return (
    <div className="doc-uploader-container">

      <div className="doc-header">
        <h2> Consultant Notes Scanner</h2>
        <span className="patient-id-pill">{selectedPatient?.name}</span>
      </div>

      {!selectedPatient ? (
        <div className="no-patient">Select a patient first</div>
      ) : (
        <>
          <div className="upload-box">
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files))}
            />
            <button className="primary-btn" onClick={handleUpload}>
               Upload & Extract Notes
            </button>
          </div>

          {structured && (
            <div className="structured-box">
              <h3>Extracted JSON (Editable)</h3>
              <textarea
                value={JSON.stringify(structured, null, 2)}
                onChange={(e) => {
                  try {
                    setStructured(JSON.parse(e.target.value));
                  } catch {}
                }}
              />

              <button className="save-btn" disabled={saving} onClick={handleSave}>
                {saving ? "Saving..." : "Save to EMR"}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
