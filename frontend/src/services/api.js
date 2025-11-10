// Arquivo: frontend/src/services/api.js
"""
O "Embaixador" da API (Cliente Axios Centralizado).

Este módulo cria uma instância 'singleton' do Axios (o 'api')
que é pré-configurada com a URL base do nosso backend.

Ele usa "interceptadores" para automatizar a lógica de
autenticação e tratamento de erros de sessão.

Todos os componentes que precisam de dados (Dashboard, Reports, etc.)
DEVEM importar 'api' daqui, em vez de usar o 'axios' puro.
"""

import axios from 'axios';

// 1. Cria a instância "pré-configurada" do axios
//    Ela lê a URL da nossa API (seja 'localhost' ou '...onrender.com')
//    do arquivo .env (através do Vite).
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

// --- 2. INTERCEPTADOR DE REQUISIÇÃO (O "Crachá Automático") ---
//
// Este interceptador é executado ANTES de cada requisição (GET, POST, PUT, DELETE)
// que usa esta instância 'api'.
api.interceptors.request.use(
  (config) => {
    // Pega o token salvo no localStorage
    const token = localStorage.getItem('token');
    
    // Se o token existir, o anexa ao cabeçalho 'Authorization'
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Deixa a requisição continuar
    return config;
  },
  (error) => {
    // (Caso raro em que a própria configuração da requisição falha)
    return Promise.reject(error);
  }
);

// --- 3. INTERCEPTADOR DE RESPOSTA (O "Segurança" do Frontend) ---
//
// Este interceptador "olha" CADA resposta que volta da API.
api.interceptors.response.use(
  
  // (Caso 1: A resposta é 2xx - SUCESSO)
  // Se a resposta for boa (ex: 200 OK), apenas a repasse
  // para o componente que a chamou (ex: 'Dashboard.jsx').
  (response) => {
    return response;
  },
  
  // (Caso 2: A resposta é 4xx ou 5xx - ERRO)
  async (error) => {
    // Verificamos se o erro é o "401 - Não Autorizado"
    // (ou seja, nosso token está vencido, inválido, ou o usuário foi deletado)
    if (error.response && error.response.status === 401) {
      console.error("Interceptador 401: Token vencido ou inválido. Deslogando...");
      
      // 1. Limpa o "crachá" vencido do localStorage
      localStorage.removeItem('token');
      
      // 2. "Chuta" o usuário de volta para a tela de login
      //
      // Decisão de Engenharia (Hard Refresh):
      // Usamos 'window.location.href' (um "hard refresh")
      // em vez do 'navigate' (do React Router). Isso FORÇA a
      // aplicação a recarregar do zero, limpando qualquer
      // estado antigo (como o 'user' no AuthContext)
      // e garantindo um logout 100% limpo.
      window.location.href = '/login'; 
    }
    
    // Para qualquer outro erro (404, 500, 422, etc.), apenas rejeite a promessa
    // para que o '.catch()' do componente (ex: no 'Reports.jsx')
    // possa tratar o erro (ex: mostrando "Não foi possível carregar os dados").
    return Promise.reject(error);
  }
);


export default api;