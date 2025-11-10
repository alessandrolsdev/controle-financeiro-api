// Arquivo: frontend/src/context/AuthContext.jsx
/*
 * Provedor de Contexto de Autenticação (O "Cérebro Global").
 *
 * Este é o componente de gerenciamento de estado mais crítico da aplicação.
 * Ele gerencia a sessão do usuário, a identidade e a sincronização offline.
 *
 * Responsabilidades:
 * 1. Armazenar o 'token' e o objeto 'user' completo.
 * 2. Fornecer as funções 'login()' e 'logout()'.
 * 3. Buscar o perfil completo do usuário ('GET /usuarios/me') após o login.
 * 4. Fornecer o estado 'isAuthLoading' para prevenir "race conditions"
 * (corridas de dados) nos componentes filhos.
 * 5. Gerenciar a "fila" de transações offline ('syncOfflineQueue')
 * e disparar o 'syncTrigger' quando a sincronização é concluída.
 */

import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios'; // Usado APENAS para o '/token' (antes do interceptador)
import api from '../services/api'; // O "Embaixador" (com interceptadores)

// 1. Cria o "Contexto" (O "cérebro" em si)
const AuthContext = createContext();

// 2. Cria o "Provedor" (O componente que "envelopa" o <App />)
export const AuthProvider = ({ children }) => {
  // --- Estados Principais ---
  
  // O 'token' (string JWT) lido do localStorage.
  const [token, setToken] = useState(localStorage.getItem('token'));
  
  // O objeto de usuário COMPLETO (vindo de 'GET /usuarios/me').
  const [user, setUser] = useState(null); 
  
  // O "Aviso" de carregamento (V7.6). Impede que os 'filhos'
  // busquem dados antes que a autenticação esteja 100% pronta.
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  
  // O "Sino" de Sincronização (V9.3). Tocado quando a fila
  // offline é descarregada, avisando o MainLayout para recarregar.
  const [syncTrigger, setSyncTrigger] = useState(0);

  /**
   * Efeito Principal [token]: Busca o Perfil do Usuário.
   *
   * Roda sempre que o 'token' mudar (login/logout)
   * ou quando a página carregar pela primeira vez.
   */
  useEffect(() => {
    const fetchUserProfile = async () => {
      if (token) {
        try {
          // Injeta o token no 'api' (nosso interceptador)
          api.defaults.headers['Authorization'] = `Bearer ${token}`;
          
          // Busca os dados completos do perfil
          const response = await api.get('/usuarios/me');
          
          // Salva o objeto de usuário completo (nome, email, etc.)
          setUser(response.data); 
          localStorage.setItem('token', token);
        } catch (error) {
          // Se o token for inválido (expirado, etc.), desloga
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
      // Avisa aos "filhos" que a autenticação terminou
      setIsAuthLoading(false);
    };

    // Avisa aos "filhos" que a autenticação começou
    setIsAuthLoading(true);
    fetchUserProfile();
  }, [token]); // <-- O gatilho é o 'token'

  
  /**
   * Efeito [isAuthLoading, token]: Sincroniza a Fila Offline.
   *
   * Roda APÓS a autenticação estar concluída E
   * se o navegador estiver online.
   */
  useEffect(() => {
    // A 'syncOfflineQueue' (abaixo) é a função que
    // descarrega a fila do localStorage.
    
    // Ouve o evento 'online' do navegador
    window.addEventListener('online', syncOfflineQueue);
    
    // Se já estivermos online E a auth estiver pronta,
    // tenta descarregar a fila imediatamente.
    if (navigator.onLine && !isAuthLoading && token) {
      syncOfflineQueue();
    }
    
    // Limpa o ouvinte
    return () => {
      window.removeEventListener('online', syncOfflineQueue);
    };
  }, [isAuthLoading, token]); // Ouve a auth e o token


  /**
   * (V9.3) Descarrega a fila de transações offline.
   * Chama o endpoint "leve" '/transacoes/sync'.
   */
  const syncOfflineQueue = async () => {
    const queue = JSON.parse(localStorage.getItem('offlineTransactionsQueue') || '[]');
    if (queue.length === 0) { return; } // Nada a fazer
    
    console.log(`SINCRONIZANDO: ${queue.length} transações pendentes...`);
    
    // (Garante que a API tem o token, caso o 'fetchUserProfile'
    //  ainda não tenha terminado)
    if (api.defaults.headers['Authorization'] === null) {
        console.warn("Sync offline pausado: token ainda não está pronto.");
        return; 
    }
    
    try {
      for (const transacao of queue) {
        // Chama a "porta dos fundos" da API (só salva, não recalcula)
        await api.post('/transacoes/sync', transacao);
      }
      
      localStorage.removeItem('offlineTransactionsQueue');
      console.log('SINCRONIZAÇÃO BEM-SUCEDIDA! Fila offline limpa.');
      
      // "Toca o sino" para o MainLayout recarregar o dashboard
      setSyncTrigger(key => key + 1); 
      
    } catch (err) {
      console.error('ERRO DE SINCRONIZAÇÃO OFFLINE:', err);
      // (Se falhar, as transações permanecem na fila
      //  para a próxima tentativa)
    }
  };

  
  /**
   * Função de Login (chamada pelo Login.jsx).
   * Apenas busca o token; o 'useEffect[token]' faz o resto.
   */
  const login = async (username, password) => {
    // (Usa 'axios' direto, pois o 'api' (interceptador)
    //  ainda não tem o token neste ponto).
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    try {
      const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/token`, formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      const newToken = response.data.access_token;
      setToken(newToken); // Define o token (o 'useEffect' fará o resto)
      return true;
    } catch (err) {
      console.error('Erro no login (AuthContext):', err);
      return false;
    }
  };

  /**
   * Função de Logout (chamada pelo Profile.jsx).
   * Apenas limpa o token; o 'useEffect[token]' faz o resto.
   */
  const logout = () => {
    setToken(null); // Limpa o token
  };

  // 3. Compartilha os valores com todos os "filhos"
  return (
    <AuthContext.Provider value={{ 
        token, 
        user, 
        isAuthLoading, 
        syncTrigger, 
        login, 
        logout 
    }}>
      {children}
    </AuthContext.Provider>
  );
};

// 4. O Hook Customizado (O "Atalho")
// (Permite que os componentes usem 'useAuth()' em vez
//  de 'useContext(AuthContext)')
export const useAuth = () => {
  return useContext(AuthContext);
};