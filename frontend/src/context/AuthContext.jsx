// Arquivo: frontend/src/context/AuthContext.jsx
// (VERSÃO V9.3 - CORREÇÃO DE SYNC OFFLINE)
/*
REATORAÇÃO (Missão V9.3 - Correção):
O 'syncOfflineQueue' foi atualizado para chamar o
NOVO endpoint "leve" ('/transacoes/sync'), que não exige
'data_inicio' ou 'data_fim' e não recalcula o dashboard.
*/

import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';
import api from '../services/api'; 

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null); 
  const [syncTrigger, setSyncTrigger] = useState(0);
  const [isAuthLoading, setIsAuthLoading] = useState(true);

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
      setIsAuthLoading(false);
    };
    setIsAuthLoading(true);
    fetchUserProfile();
  }, [token]);

  
  // --- LÓGICA DE SINCRONIZAÇÃO OFFLINE (A CORREÇÃO ESTÁ AQUI) ---
  const syncOfflineQueue = async () => {
    const queue = JSON.parse(localStorage.getItem('offlineTransactionsQueue') || '[]');
    if (queue.length === 0) { return; }
    
    console.log(`SINCRONIZANDO: ${queue.length} transações pendentes...`);
    
    // (Garante que a API tem o token, caso o 'fetchUserProfile'
    //  ainda não tenha terminado)
    if (api.defaults.headers['Authorization'] === null) {
        console.warn("Sync offline pausado: token ainda não está pronto.");
        return; 
    }
    
    try {
      for (const transacao of queue) {
        // A MUDANÇA: Chama a nova rota "leve" ('/sync')
        // que não precisa das datas de filtro.
        await api.post('/transacoes/sync', transacao);
      }
      
      localStorage.removeItem('offlineTransactionsQueue');
      console.log('SINCRONIZAÇÃO BEM-SUCEDIDA! Fila offline limpa.');
      
      // "Toca o sino" para o MainLayout
      setSyncTrigger(key => key + 1); 
      
    } catch (err) {
      console.error('ERRO DE SINCRONIZAÇÃO OFFLINE:', err);
      // (Se falhar, as transações permanecem na fila
      //  para a próxima tentativa)
    }
  };
  
  useEffect(() => {
    window.addEventListener('online', syncOfflineQueue);
    // (A lógica de 'isAuthLoading' impede que isso rode
    //  antes do token estar pronto)
    if (navigator.onLine && !isAuthLoading && token) {
      syncOfflineQueue();
    }
    return () => {
      window.removeEventListener('online', syncOfflineQueue);
    };
  }, [isAuthLoading, token]); // <-- Ouve 'isAuthLoading'

  
  // Funções de Login e Logout
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
      // (Não chamamos 'syncOfflineQueue' aqui, pois o 'useEffect[token]'
      //  vai lidar com isso de forma mais segura)
      return true;
    } catch (err) {
      console.error('Erro no login (AuthContext):', err);
      return false;
    }
  };
  const logout = () => {
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ token, user, login, logout, syncTrigger, isAuthLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  return useContext(AuthContext);
};