import './PatientDetails.css';

function PatientDetails({ patient, onClose }) {
  if (!patient) {
    return (
      <div className="patient-details-container">
        <div className="no-selection">
          <h2>Select a patient to view details</h2>
          <p>Choose a patient from the list to see their complete medical record</p>
        </div>
      </div>
    );
  }

  return (
    <div className="patient-details-container">
      <div className="details-header">
        <div>
          <h2>{patient.name}</h2>
          <span className="patient-id-badge">{patient.id}</span>
        </div>
        <button className="close-btn" onClick={onClose}>✕</button>
      </div>

      <div className="details-content">
        <div className="info-section">
          <h3>Personal Information</h3>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">Age</span>
              <span className="info-value">{patient.age} years</span>
            </div>
            <div className="info-item">
              <span className="info-label">Phone</span>
              <span className="info-value">{patient.phone}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Last Visit</span>
              <span className="info-value">{patient.lastVisit}</span>
            </div>
          </div>
        </div>

        <div className="info-section">
          <h3>Medical Condition</h3>
          <div className="condition-badge">
            {patient.condition}
          </div>
        </div>

        <div className="info-section">
          <h3>Medical History</h3>
          <div className="history-list">
            {patient.history && patient.history.length > 0 ? (
              patient.history.map((item, index) => (
                <div key={index} className="history-item">
                  <span className="history-icon">✓</span>
                  {item}
                </div>
              ))
            ) : (
              <p className="no-history">No medical history recorded</p>
            )}
          </div>
        </div>

        {patient.notes && patient.notes.length > 0 && (
          <div className="info-section">
            <h3>Clinical Notes</h3>
            <div className="notes-list">
              {patient.notes.map((note, index) => (
                <div key={index} className="note-item">
                  <div className="note-header">Note {index + 1}</div>
                  <div className="note-content">
                    {typeof note === 'string' ? note : JSON.stringify(note, null, 2)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default PatientDetails;
