import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

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
