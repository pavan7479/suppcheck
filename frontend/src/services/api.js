import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const analyzeFormulation = async (data) => {
  const response = await api.post('/analyze', data);
  return response.data;
};

export const searchIngredients = async (query) => {
  const response = await api.get('/search', { params: { q: query } });
  return response.data;
};
