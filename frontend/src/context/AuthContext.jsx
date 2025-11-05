// Arquivo: frontend/src/context/AuthContext.jsx
// (VERSÃO FINAL COM DECODIFICAÇÃO DE TOKEN)

import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';
import api from '../services/api';
import { jwtDecode } from 'jwt-decode'; // 1. IMPORTA A NOVA FERRAMENTA

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  
  // --- 2. NOVO ESTADO PARA O OBJETO DO USUÁRIO ---
  // Vai guardar os dados de dentro do token (ex: { sub: 'admin', exp: 12345 })
  const [user, setUser] = useState(null); 
  
  const [syncTrigger, setSyncTrigger] = useState(0);

  // --- 3. NOVO 'useEffect' PARA LER O TOKEN ---
  // Este efeito "ouve" qualquer mudança no 'token'
  useEffect(() => {
    if (token) {
      try {
        // Se o token existe, decodifica ele
        const decodedToken = jwtDecode(token); 
        setUser(decodedToken); // Salva os dados (ex: { sub: 'admin', exp: ... }) no estado
        localStorage.setItem('token', token); // Garante que o token está salvo
      } catch (error) {
        // Se o token estiver corrompido ou for inválido
        console.error("Token inválido. Deslogando.", error);
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
      }
    } else {
      // Se o token for nulo (logout)
      localStorage.removeItem('token');
      setUser(null);
    }
  }, [token]); // Roda toda vez que o 'token' mudar

  // ... (função syncOfflineQueue - sem alteração) ...
  const syncOfflineQueue = async () => {
    const queue = JSON.parse(localStorage.getItem('offlineTransactionsQueue') || '[]');
    if (queue.length === 0) { return; }
    console.log(`SINCRONIZANDO: ${queue.length} transações pendentes...`);
    try {
      for (const transacao of queue) {
        await api.post('/transacoes/', transacao);
      }
      localStorage.removeItem('offlineTransactionsQueue');
      console.log('SINCRONIZAÇÃO BEM-SUCEDIDA! Fila offline limpa.');
      setSyncTrigger(key => key + 1); 
    } catch (err) {
      console.error('ERRO DE SINCRONIZAÇÃO OFFLINE:', err);
    }
  };
  useEffect(() => {
    window.addEventListener('online', syncOfflineQueue);
    if (navigator.onLine) {
      syncOfflineQueue();
    }
    return () => {
      window.removeEventListener('online', syncOfflineQueue);
    };
  }, []);

  
  // --- 4. Função de Login (Simplificada) ---
  const login = async (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
      const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/token`, formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      const newToken = response.data.access_token;
      // APENAS salvamos o token. O 'useEffect' acima vai
      // cuidar de decodificar e salvar o 'user' automaticamente.
      setToken(newToken); 
      
      syncOfflineQueue();
      return true;
    } catch (err) {
      console.error('Erro no login (AuthContext):', err);
      return false;
    }
  };

  // --- 5. Função de Logout (Simplificada) ---
  const logout = () => {
    // APENAS limpamos o token. O 'useEffect' acima vai
    // cuidar de limpar o 'user' automaticamente.
    setToken(null); 
  };

  // --- 6. COMPARTILHANDO TUDO (INCLUINDO O 'user') ---
  return (
    <AuthContext.Provider value={{ token, user, login, logout, syncTrigger }}>
      {children}
    </AuthContext.Provider>
  );
};

// --- 7. Hook "useAuth" (código existente) ---
export const useAuth = () => {
  return useContext(AuthContext);
};