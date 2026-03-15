import { useState, useEffect } from 'react';
import './AddPatientModal.css';

function AddPatientModal({ isOpen, onClose, onSave, editingPatient }) {
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    age: '',
    condition: '',
    history: '',
    lastVisit: '',
    phone: ''
  });

  useEffect(() => {
    if (editingPatient) {
      setFormData({
        id: editingPatient.id || '',
        name: editingPatient.name || '',
        age: editingPatient.age || '',
        condition: editingPatient.condition || '',
        history: editingPatient.history ? editingPatient.history.join(', ') : '',
        lastVisit: editingPatient.lastVisit || '',
        phone: editingPatient.phone || ''
      });
    } else {
      setFormData({
        id: '',
        name: '',
        age: '',
        condition: '',
        history: '',
        lastVisit: '',
        phone: ''
      });
    }
  }, [editingPatient, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const patientData = {
      ...formData,
      age: parseInt(formData.age),
      history: formData.history.split(',').map(item => item.trim()).filter(item => item)
    };
    onSave(patientData);
    onClose();
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{editingPatient ? 'Edit Patient' : 'Add New Patient'}</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit} className="patient-form">
          <div className="form-row">
            <div className="form-group">
              <label>Patient ID</label>
              <input
                type="text"
                name="id"
                value={formData.id}
                onChange={handleChange}
                placeholder="e.g., P001"
                required
              />
            </div>
            <div className="form-group">
              <label>Full Name</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="Enter patient name"
                required
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Age</label>
              <input
                type="number"
                name="age"
                value={formData.age}
                onChange={handleChange}
                placeholder="Enter age"
                required
              />
            </div>
            <div className="form-group">
              <label>Phone</label>
              <input
                type="tel"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                placeholder="+1-555-0000"
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label>Medical Condition</label>
            <input
              type="text"
              name="condition"
              value={formData.condition}
              onChange={handleChange}
              placeholder="Enter diagnosis"
              required
            />
          </div>

          <div className="form-group">
            <label>Last Visit Date</label>
            <input
              type="date"
              name="lastVisit"
              value={formData.lastVisit}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label>Medical History</label>
            <textarea
              name="history"
              value={formData.history}
              onChange={handleChange}
              placeholder="Enter medical history (comma-separated)"
              rows="3"
            />
          </div>

          <div className="form-actions">
            <button type="button" className="btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-submit">
              {editingPatient ? 'Update Patient' : 'Add Patient'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddPatientModal;
