// Arquivo: frontend/src/services/api.js
// Responsabilidade: O "Mensageiro" Centralizado da Aplicação.
//
// Este arquivo é o "coração" da nossa comunicação com o backend.
// Nós criamos uma 'instância' do Axios pré-configurada para que
// nenhum outro componente (Dashboard, Settings, etc.) precise saber
// a URL completa da API ou como se autenticar.

import axios from 'axios';

// 1. Cria a instância "pré-configurada" do axios
const api = axios.create({
  
  // 2. Lê a URL base do nosso backend a partir das variáveis de ambiente.
  // Em desenvolvimento (npm run dev), ele lerá do 'frontend/.env' (http://127.0.0.1:8000).
  // Em produção (no Vercel), ele lerá a variável VITE_API_BASE_URL
  // que configuramos no painel do Vercel (https://...onrender.com).
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

// --- 3. O INTERCEPTADOR MÁGICO (O "Crachá" Automático) ---
//
// 'interceptors.request' "ensina" o axios a fazer algo ANTES
// de CADA requisição que ele enviar (ex: GET, POST, etc.).
api.interceptors.request.use(
  (config) => {
    // 1. Pega o token do localStorage (o "crachá" que guardamos no AuthContext)
    const token = localStorage.getItem('token');
    
    // 2. Se o token existir, adiciona ele no cabeçalho da requisição
    //    no formato 'Authorization: Bearer <token>'
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // 3. Continua com a requisição, agora com o cabeçalho de autorização
    return config;
  },
  (error) => {
    // Em caso de erro ao preparar a requisição (ex: falha de rede)
    return Promise.reject(error);
  }
);

// Exporta a instância 'api' configurada para ser usada em todo o app.
// Ex: import api from '../../services/api';
export default api;