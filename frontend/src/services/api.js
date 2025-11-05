// Arquivo: frontend/src/services/api.js
// (VERSÃO FINAL COM INTERCEPTADOR DE ERRO 401)

import axios from 'axios';

// 1. Cria a instância "pré-configurada" do axios
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

// --- 2. O INTERCEPTADOR DE REQUISIÇÃO (O "Crachá" Automático) ---
// (Este código você já tem)
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

// --- 3. O INTERCEPTADOR DE RESPOSTA (O "Segurança" do Frontend) ---
//
// Este interceptador "olha" CADA resposta que volta da API.
api.interceptors.response.use(
  
  // (Caso 1: A resposta é 2xx - SUCESSO)
  // Se a resposta for boa, apenas a repasse.
  (response) => {
    return response;
  },
  
  // (Caso 2: A resposta é 4xx ou 5xx - ERRO)
  // Se a API retornar um erro...
  async (error) => {
    // Verificamos se o erro é o "401 - Não Autorizado"
    // (ou seja, nosso token está vencido ou inválido)
    if (error.response && error.response.status === 401) {
      console.error("Token vencido ou inválido detectado. Deslogando...");
      
      // 1. Limpa o "crachá" vencido do bolso
      localStorage.removeItem('token');
      
      // 2. "Chuta" o usuário de volta para a tela de login
      //    (Isso força o AuthContext a recarregar sem token)
      //    Usamos window.location para forçar um recarregamento total da página,
      //    limpando qualquer estado antigo do React.
      window.location.href = '/login'; 
    }
    
    // Para qualquer outro erro (404, 500, etc.), apenas rejeite a promessa
    // para que os componentes (ex: Dashboard) possam tratar
    return Promise.reject(error);
  }
);


export default api;