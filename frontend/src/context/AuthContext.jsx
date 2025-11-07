// Arquivo: frontend/src/context/AuthContext.jsx
// (VERSÃO V7.1 - BUSCA O PERFIL COMPLETO NO LOGIN)
/*
REATORAÇÃO (Missão V7.1):
Este é o "Cérebro" atualizado.
1. O estado 'user' agora armazena o OBJETO DE USUÁRIO COMPLETO
   (vindo de /usuarios/me), não apenas os dados do token.
2. O 'useEffect[token]' agora é o responsável por buscar o
   perfil do usuário. Ele roda no login ou no carregamento da página.
3. O 'login' e 'logout' apenas manipulam o 'token'; o 'useEffect'
   reage a essa mudança.
4. O 'user.nome_completo' estará disponível para todo o app.
*/

import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';
import api from '../services/api'; // O "Embaixador"
import { jwtDecode } from 'jwt-decode';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  
  // 1. ESTE ESTADO AGORA É O OBJETO DE USUÁRIO COMPLETO
  const [user, setUser] = useState(null); 
  
  const [syncTrigger, setSyncTrigger] = useState(0);

  // 2. O NOVO 'useEffect' QUE BUSCA O PERFIL
  useEffect(() => {
    // Esta função roda sempre que o 'token' mudar (login/logout)
    // ou quando a página carregar pela primeira vez.
    const fetchUserProfile = async () => {
      if (token) {
        try {
          // Garante que o 'api.js' (nosso interceptador)
          // use o token mais recente que temos no estado.
          api.defaults.headers['Authorization'] = `Bearer ${token}`;
          
          // Busca os dados completos do perfil
          const response = await api.get('/usuarios/me');
          
          // Salva o objeto de usuário completo no estado
          setUser(response.data); 
          
          localStorage.setItem('token', token);
        } catch (error) {
          // Se o token for inválido (ex: expirado), desloga o usuário
          console.error("Token inválido ou sessão expirou. Deslogando.", error);
          localStorage.removeItem('token');
          setToken(null);
          setUser(null);
        }
      } else {
        // Se não há token, limpa tudo
        localStorage.removeItem('token');
        api.defaults.headers['Authorization'] = null;
        setUser(null);
      }
    };

    fetchUserProfile();
  }, [token]); // Roda toda vez que o 'token' mudar

  
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

  
  // 3. Função de Login (Simplificada)
  // (Ela só precisa definir o token; o 'useEffect' fará o resto)
  const login = async (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
      const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/token`, formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      const newToken = response.data.access_token;
      setToken(newToken); // <-- Define o token
      
      syncOfflineQueue();
      return true;
    } catch (err) {
      console.error('Erro no login (AuthContext):', err);
      return false;
    }
  };

  // 4. Função de Logout (Simplificada)
  const logout = () => {
    setToken(null); // <-- Limpa o token (o 'useEffect' fará o resto)
  };

  // 5. COMPARTILHA O 'user' COMPLETO
  return (
    <AuthContext.Provider value={{ token, user, login, logout, syncTrigger }}>
      {children}
    </AuthContext.Provider>
  );
};

// --- Hook "useAuth" (Sem mudança) ---
export const useAuth = () => {
  return useContext(AuthContext);
};