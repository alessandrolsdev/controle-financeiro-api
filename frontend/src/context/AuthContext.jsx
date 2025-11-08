// Arquivo: frontend/src/context/AuthContext.jsx
// (VERSÃO V7.6 - CORREÇÃO DE RACE CONDITION)
/*
REATORAÇÃO (Missão V7.6):
1. Adiciona o novo estado 'isAuthLoading'.
2. 'isAuthLoading' é 'true' no início e enquanto
   'fetchUserProfile' está rodando.
3. 'isAuthLoading' é 'false' APÓS o perfil ser
   carregado (ou falhar).
4. Compartilha 'isAuthLoading' com toda a aplicação.
*/

import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';
import api from '../services/api';
// (Não precisamos mais do jwtDecode, pois o 'user' vem da API)
// import { jwtDecode } from 'jwt-decode'; 

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null); 
  const [syncTrigger, setSyncTrigger] = useState(0);
  
  // 1. O NOVO ESTADO DE "AVISO"
  const [isAuthLoading, setIsAuthLoading] = useState(true);

  // 2. O 'useEffect' ATUALIZADO
  useEffect(() => {
    const fetchUserProfile = async () => {
      if (token) {
        try {
          api.defaults.headers['Authorization'] = `Bearer ${token}`;
          const response = await api.get('/usuarios/me');
          setUser(response.data); 
          localStorage.setItem('token', token);
        } catch (error) {
          console.error("Token inválido ou sessão expirou. Deslogando.", error);
          localStorage.removeItem('token');
          setToken(null);
          setUser(null);
        }
      } else {
        localStorage.removeItem('token');
        api.defaults.headers['Authorization'] = null;
        setUser(null);
      }
      // 3. AVISA QUE A AUTENTICAÇÃO TERMINOU (sucesso ou falha)
      setIsAuthLoading(false);
    };

    // 4. AVISA QUE A AUTENTICAÇÃO COMEÇOU
    setIsAuthLoading(true);
    fetchUserProfile();
  }, [token]);

  
  // (Lógica de Sincronização Offline - Sem mudança)
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

  
  // Funções de Login e Logout (Sem mudança)
  const login = async (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    try {
      const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/token`, formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      const newToken = response.data.access_token;
      setToken(newToken);
      syncOfflineQueue();
      return true;
    } catch (err) {
      console.error('Erro no login (AuthContext):', err);
      return false;
    }
  };
  const logout = () => {
    setToken(null);
  };

  // 5. COMPARTILHA O NOVO ESTADO
  return (
    <AuthContext.Provider value={{ token, user, login, logout, syncTrigger, isAuthLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  return useContext(AuthContext);
};