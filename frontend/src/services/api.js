// Arquivo: frontend/src/services/api.js
/**
 * @file Cliente HTTP Centralizado (Axios).
 * @description Configuração de uma instância Axios com interceptadores para autenticação e tratamento global de erros.
 */

import axios from 'axios';

/**
 * Instância do Axios pré-configurada com a URL base da API.
 * A URL é obtida das variáveis de ambiente (VITE_API_BASE_URL).
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

/**
 * Interceptador de Requisição.
 *
 * Antes de cada requisição ser enviada, verifica se existe um token JWT no localStorage.
 * Se existir, adiciona o token ao cabeçalho Authorization da requisição.
 */
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Interceptador de Resposta.
 *
 * Processa as respostas da API. Em caso de erro 401 (Não Autorizado), realiza logout automático:
 * limpa o token armazenado e redireciona o usuário para a página de login.
 */
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    if (error.response && error.response.status === 401) {
      console.error("Interceptador 401: Token vencido ou inválido. Deslogando...");
      
      localStorage.removeItem('token');
      
      // Força um recarregamento da página para garantir limpeza de estado
      window.location.href = '/login'; 
    }
    
    return Promise.reject(error);
  }
);


export default api;
