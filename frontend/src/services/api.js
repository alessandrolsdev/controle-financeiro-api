// Arquivo: frontend/src/services/api.js

import axios from 'axios';

// Cria uma instância "pré-configurada" do axios
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000', // A URL base do nosso backend
});

// --- O INTERCEPTADOR MÁGICO ---
// Isso "ensina" o axios a fazer algo antes de CADA requisição
api.interceptors.request.use(
  (config) => {
    // 1. Pega o token do localStorage (o "crachá" que guardamos)
    const token = localStorage.getItem('token');
    
    // 2. Se o token existir, adiciona ele no cabeçalho da requisição
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    return config; // Continua com a requisição
  },
  (error) => {
    // Em caso de erro ao preparar a requisição
    return Promise.reject(error);
  }
);

export default api;