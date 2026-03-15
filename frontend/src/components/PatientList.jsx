import { useState } from 'react';
import './PatientList.css';

function PatientList({ patients, onSelectPatient, onDeletePatient, onEditPatient }) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredPatients = patients.filter(patient =>
    patient.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    patient.condition.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="patient-list-container">
      <div className="patient-list-header">
        <h2>Patient Records</h2>
        <input
          type="text"
          placeholder="Search patients..."
          className="search-input"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      <div className="patient-list">
        {filteredPatients.length === 0 ? (
          <p className="no-patients">No patients found</p>
        ) : (
          filteredPatients.map(patient => (
            <div
              key={patient.id}
              className="patient-card"
              onClick={() => onSelectPatient(patient)}
            >
              <div className="patient-card-header">
                <h3>{patient.name}</h3>
                <span className="patient-id">{patient.id}</span>
              </div>
              <div className="patient-info">
                <p><strong>Age:</strong> {patient.age}</p>
                <p><strong>Condition:</strong> {patient.condition}</p>
                <p><strong>Last Visit:</strong> {patient.lastVisit}</p>
                <p><strong>Phone:</strong> {patient.phone}</p>
              </div>
              <div className="patient-actions">
                <button
                  className="btn-edit"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEditPatient(patient);
                  }}
                >
                  Edit
                </button>
                <button
                  className="btn-delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeletePatient(patient.name);
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default PatientList;
