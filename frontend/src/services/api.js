// Arquivo: frontend/src/services/api.js
// (CRIE ESTE ARQUIVO)

import axios from 'axios';

// 1. Cria a instância do Axios com a URL base do seu backend
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000',
});

// 2. O Interceptor (Porteiro)
api.interceptors.request.use(
  (config) => {
    // 3. Pega o token do localStorage
    const token = localStorage.getItem('authToken'); 

    if (token) {
      // 4. Adiciona o token no cabeçalho
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;