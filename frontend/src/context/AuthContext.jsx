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
 * Remove do dispositivo qualquer cache de resposta da API.
 *
 * Versões anteriores do PWA armazenavam respostas autenticadas — saldos e
 * extrato — no Cache Storage por até 7 dias. Essa configuração foi removida,
 * mas as entradas já gravadas continuam no disco de quem tem o app instalado
 * até serem apagadas explicitamente.
 *
 * @returns {Promise<void>} Conclui quando os caches tiverem sido removidos.
 */
export const limparCachesDaAplicacao = async () => {
  if (typeof caches === 'undefined') { return; }

  try {
    const nomes = await caches.keys();
    await Promise.all(
      nomes
        .filter((nome) => nome.startsWith('api-cache'))
        .map((nome) => caches.delete(nome))
    );
  } catch (err) {
    console.warn('Não foi possível limpar os caches da aplicação:', err);
  }
};

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

    if (!localStorage.getItem('token')) {
      console.warn('Sync offline pausado: sem sessão autenticada.');
      return;
    }

    console.log(`SINCRONIZANDO: ${queue.length} transações pendentes...`);

    /*
     * Cada item é enviado individualmente e removido da fila só depois de
     * confirmado. A versão anterior chamava POST /transacoes/sync — um endpoint
     * que não existe no backend — dentro de um único try/catch que apagava a
     * fila inteira ao final. Na prática, toda sincronização falhava com 404 e,
     * pior, um erro no meio do laço descartava lançamentos já enviados.
     *
     * O cabeçalho Idempotency-Key garante que reenviar um item após uma queda
     * de conexão não gere um lançamento financeiro duplicado.
     */
    const pendentes = [];
    let sincronizou = false;

    for (const item of queue) {
      const { chaveIdempotencia, periodo, ...transacao } = item;

      try {
        await api.post('/transacoes/', transacao, {
          params: periodo,
          headers: { 'Idempotency-Key': chaveIdempotencia },
        });
        sincronizou = true;
      } catch (err) {
        const status = err.response?.status;

        // 4xx (exceto 429) indica payload permanentemente inválido: reenviar
        // não vai resolver e manteria o item preso na fila para sempre.
        if (status && status >= 400 && status < 500 && status !== 429) {
          console.error('Lançamento offline descartado por ser inválido:', status);
          continue;
        }

        // Falha de rede ou erro do servidor: preserva para a próxima tentativa.
        pendentes.push(item);
      }
    }

    if (pendentes.length > 0) {
      localStorage.setItem('offlineTransactionsQueue', JSON.stringify(pendentes));
      console.warn(`${pendentes.length} lançamento(s) ainda pendente(s).`);
    } else {
      localStorage.removeItem('offlineTransactionsQueue');
      console.log('SINCRONIZAÇÃO BEM-SUCEDIDA! Fila offline limpa.');
    }

    if (sincronizou) {
      setSyncTrigger(key => key + 1);
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
   * Além de limpar o token, apaga todo dado financeiro que tenha ficado no
   * dispositivo: a fila offline e quaisquer caches de API remanescentes de
   * versões anteriores do PWA. Sem isso, em um computador compartilhado o
   * próximo usuário poderia recuperar o extrato do anterior.
   *
   * @returns {Promise<void>} Conclui após a limpeza do armazenamento local.
   */
  const logout = async () => {
    localStorage.removeItem('token');
    localStorage.removeItem('offlineTransactionsQueue');

    await limparCachesDaAplicacao();

    setToken(null);
    setUser(null);
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
