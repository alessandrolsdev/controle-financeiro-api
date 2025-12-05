// Arquivo: frontend/src/context/AuthContext.jsx
/**
 * @file Contexto de Autenticação.
 * @description Gerencia o estado global de autenticação, perfil do usuário e sincronização offline.
 */

import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';
import api from '../services/api';

/**
 * Contexto que armazena os dados de autenticação.
 */
const AuthContext = createContext();

/**
 * Provedor de Autenticação.
 *
 * Envolve a aplicação para fornecer acesso ao estado de autenticação.
 * Gerencia o ciclo de vida do token JWT, busca dados do usuário e sincroniza transações offline.
 *
 * @param {object} props - Propriedades do componente.
 * @param {React.ReactNode} props.children - Componentes filhos que terão acesso ao contexto.
 * @returns {JSX.Element} O provedor de contexto.
 */
export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null); 
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [syncTrigger, setSyncTrigger] = useState(0);

  /**
   * Efeito colateral que monitora o token de autenticação.
   *
   * Quando o token muda:
   * 1. Configura o header de autorização na instância da API.
   * 2. Busca os dados atualizados do perfil do usuário.
   * 3. Gerencia a persistência do token no localStorage.
   * 4. Trata erros de autenticação (logout forçado).
   */
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

  /**
   * Efeito colateral para sincronização de dados offline.
   *
   * Monitora o status de conexão e a autenticação. Tenta enviar dados pendentes
   * quando a conexão é restabelecida.
   */
  useEffect(() => {
    window.addEventListener('online', syncOfflineQueue);
    
    if (navigator.onLine && !isAuthLoading && token) {
      syncOfflineQueue();
    }
    
    return () => {
      window.removeEventListener('online', syncOfflineQueue);
    };
  }, [isAuthLoading, token]);


  /**
   * Sincroniza a fila de transações armazenadas offline com o backend.
   *
   * Lê a fila do localStorage e envia cada transação para a API.
   * Dispara um gatilho de atualização global após o sucesso.
   */
  const syncOfflineQueue = async () => {
    const queue = JSON.parse(localStorage.getItem('offlineTransactionsQueue') || '[]');
    if (queue.length === 0) { return; }
    
    console.log(`SINCRONIZANDO: ${queue.length} transações pendentes...`);
    
    if (api.defaults.headers['Authorization'] === null) {
        console.warn("Sync offline pausado: token ainda não está pronto.");
        return; 
    }
    
    try {
      for (const transacao of queue) {
        // Nota: O endpoint /transacoes/sync foi removido/alterado no backend, ajustando para usar o endpoint padrão se necessário, ou assumindo que o endpoint existe.
        // Como o backend removeu o /sync, vamos usar o POST padrão /transacoes/
        // Porém, o código original usava /transacoes/sync. Vou manter a lógica original documentada, mas alertando.
        // Se o endpoint não existe mais, isso falhará.
        // Assumindo que a fila contém payloads válidos para criação.
        // O código original tentava usar /transacoes/sync. Se ele não existe, isso deveria ser /transacoes/.
        // Vou manter como estava para documentação fiel, mas idealmente isso seria corrigido no código.
        // Como a instrução é apenas documentar, mantenho o código e descrevo o que faz.
        await api.post('/transacoes/sync', transacao);
      }
      
      localStorage.removeItem('offlineTransactionsQueue');
      console.log('SINCRONIZAÇÃO BEM-SUCEDIDA! Fila offline limpa.');
      
      setSyncTrigger(key => key + 1); 
      
    } catch (err) {
      console.error('ERRO DE SINCRONIZAÇÃO OFFLINE:', err);
    }
  };

  /**
   * Realiza o login do usuário.
   *
   * Envia as credenciais para o backend e armazena o token recebido.
   *
   * @param {string} username - O nome de usuário.
   * @param {string} password - A senha do usuário.
   * @returns {Promise<boolean>} Retorna true se o login for bem-sucedido, false caso contrário.
   */
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
      return true;
    } catch (err) {
      console.error('Erro no login (AuthContext):', err);
      return false;
    }
  };

  /**
   * Realiza o logout do usuário.
   *
   * Limpa o token de autenticação, o que dispara a limpeza do estado via useEffect.
   */
  const logout = () => {
    setToken(null);
  };

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

/**
 * Hook personalizado para acessar o contexto de autenticação.
 *
 * @returns {object} O contexto de autenticação (token, user, login, logout, etc.).
 */
export const useAuth = () => {
  return useContext(AuthContext);
};
