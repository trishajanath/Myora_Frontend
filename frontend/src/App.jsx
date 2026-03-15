import { useState, useEffect } from 'react';
import './App.css';
import PatientList from './components/PatientList';
import PatientDetails from './components/PatientDetails';
import AddPatientModal from './components/AddPatientModal';
import VoiceRecorder from './components/VoiceRecorder';
import ConsultantNotes from './components/ConsultantNotes';
import { patientAPI } from './services/api';

function App() {
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPatient, setEditingPatient] = useState(null);
  const [activeTab, setActiveTab] = useState('patients');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPatients();
  }, []);

  const fetchPatients = async () => {
    try {
      setLoading(true);
      const response = await patientAPI.getAll();
      if (response.status === 'success') {
        setPatients(response.data);
      }
    } catch (error) {
      console.error('Error fetching patients:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddPatient = async (patientData) => {
    try {
      const response = await patientAPI.add(patientData);
      if (response.status === 'success') {
        fetchPatients();
      }
    } catch (error) {
      console.error('Error adding patient:', error);
      alert('Failed to add patient');
    }
  };

  const handleEditPatient = async (patientData) => {
    try {
      const response = await patientAPI.update(editingPatient.name, patientData);
      if (response.status === 'success') {
        fetchPatients();
        setEditingPatient(null);
      }
    } catch (error) {
      console.error('Error updating patient:', error);
      alert('Failed to update patient');
    }
  };

  const handleDeletePatient = async (patientName) => {
    if (window.confirm(`Are you sure you want to delete ${patientName}?`)) {
      try {
        const response = await patientAPI.delete(patientName);
        if (response.status === 'success') {
          fetchPatients();
          if (selectedPatient && selectedPatient.name === patientName) {
            setSelectedPatient(null);
          }
        }
      } catch (error) {
        console.error('Error deleting patient:', error);
        alert('Failed to delete patient');
      }
    }
  };

  const openEditModal = (patient) => {
    setEditingPatient(patient);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingPatient(null);
  };

  const handleSavePatient = (patientData) => {
    if (editingPatient) {
      handleEditPatient(patientData);
    } else {
      handleAddPatient(patientData);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>Myora</h1>
          <button className="btn-add-patient" onClick={() => setIsModalOpen(true)}>
            + Add Patient
          </button>
        </div>
      </header>

      <div className="app-tabs">
        <button
          className={`tab-btn ${activeTab === 'patients' ? 'active' : ''}`}
          onClick={() => setActiveTab('patients')}
        >
          Patient Records
        </button>
        <button
          className={`tab-btn ${activeTab === 'voice' ? 'active' : ''}`}
          onClick={() => setActiveTab('voice')}
        >
          Voice Notes
        </button>
        <button
          className={`tab-btn ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveTab('documents')}
        >
          Documents
        </button>
      </div>

      <main className="app-main">
        {loading ? (
          <div className="loading-container">
            <div className="loader"></div>
            <p>Loading patients...</p>
          </div>
        ) : (
          <>
            {activeTab === 'patients' && (
              <div className="patients-view">
                <div className="left-panel">
                  <PatientList
                    patients={patients}
                    onSelectPatient={setSelectedPatient}
                    onDeletePatient={handleDeletePatient}
                    onEditPatient={openEditModal}
                  />
                </div>
                <div className="right-panel">
                  <PatientDetails
                    patient={selectedPatient}
                    onClose={() => setSelectedPatient(null)}
                  />
                </div>
              </div>
            )}

            {activeTab === 'voice' && (
              <div className="voice-view">
                <div className="left-panel">
                  <PatientList
                    patients={patients}
                    onSelectPatient={setSelectedPatient}
                    onDeletePatient={handleDeletePatient}
                    onEditPatient={openEditModal}
                  />
                </div>
                <div className="right-panel">
                  <VoiceRecorder selectedPatient={selectedPatient} onNoteSaved={fetchPatients} />
                </div>
              </div>
            )}

            {activeTab === 'documents' && (
              <div className="voice-view">
                <div className="left-panel">
                  <PatientList
                    patients={patients}
                    onSelectPatient={setSelectedPatient}
                    onDeletePatient={handleDeletePatient}
                    onEditPatient={openEditModal}
                  />
                </div>
                <div className="right-panel">
                  <ConsultantNotes selectedPatient={selectedPatient} />
                </div>
              </div>
            )}
          </>
        )}
      </main>

      <AddPatientModal
        isOpen={isModalOpen}
        onClose={closeModal}
        onSave={handleSavePatient}
        editingPatient={editingPatient}
      />
    </div>
  );
}

export default App;
