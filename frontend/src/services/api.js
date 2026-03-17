import axios from 'axios';

const API_BASE_URL = 'http://localhost:5001/api';

export const patientAPI = {
  getAll: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/patients/`);
      return response.data;
    } catch (error) {
      console.error('Error fetching patients:', error);
      throw error;
    }
  },

  add: async (patientData) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/patients/`, patientData);
      return response.data;
    } catch (error) {
      console.error('Error adding patient:', error);
      throw error;
    }
  },

  update: async (patientName, updatedData) => {
    try {
      const response = await axios.put(
        `${API_BASE_URL}/patients/?name=${encodeURIComponent(patientName)}`,
        updatedData
      );
      return response.data;
    } catch (error) {
      console.error('Error updating patient:', error);
      throw error;
    }
  },

  delete: async (patientName) => {
    try {
      const response = await axios.delete(
        `${API_BASE_URL}/patients/?name=${encodeURIComponent(patientName)}`
      );
      return response.data;
    } catch (error) {
      console.error('Error deleting patient:', error);
      throw error;
    }
  },

  getNotes: async (patientName) => {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/patients/notes?name=${encodeURIComponent(patientName)}`
      );
      return response.data;
    } catch (error) {
      console.error('Error fetching patient notes:', error);
      throw error;
    }
  }
};

export const consultantAPI = {
  extractNotes: async (files) => {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    const response = await axios.post(
      `${API_BASE_URL}/consultant/extract_notes`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  saveNotes: async (patientId, extractedJson) => {
    const response = await axios.post(`${API_BASE_URL}/consultant/save_notes`, {
      patient_id: patientId,
      extracted_json: extractedJson,
    });
    return response.data;
  },

  getNotes: async (patientId) => {
    const response = await axios.get(
      `${API_BASE_URL}/consultant/get_notes/${encodeURIComponent(patientId)}`
    );
    if (Array.isArray(response.data)) return response.data;
    if (Array.isArray(response.data?.notes)) return response.data.notes;
    return [];
  },
};

export const auditAPI = {
  getLogs: async ({ patientId, action, limit } = {}) => {
    const params = new URLSearchParams();
    if (patientId) params.set('patient_id', patientId);
    if (action) params.set('action', action);
    if (limit) params.set('limit', String(limit));
    const response = await axios.get(
      `http://localhost:5001/api/audit?${params.toString()}`
    );
    return response.data;
  },
};

export const drugSafetyAPI = {
  check: async ({ allergies, medications, diagnosis, patient_id }) => {
    const response = await axios.post(`${API_BASE_URL}/drug-safety/check`, {
      allergies,
      medications,
      diagnosis,
      patient_id,
    });
    return response.data;
  },
};
