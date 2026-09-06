// Arquivo: frontend/src/context/AuthContext.jsx
/**
 * @file Contexto de Autenticação.
 * @description Estado global de sessão, perfil e sincronização offline.
 *
 * A sessão vive em cookies httpOnly gerenciados pelo servidor. Este contexto
 * não guarda token algum: ele apenas descobre, perguntando ao backend quem é o
 * usuário, se existe uma sessão válida. É por isso que não há mais leitura de
 * `localStorage` para autenticação.
 */

import { useCallback, useEffect, useState } from 'react';

import api, { limparCachesDaApi } from '../services/api';
import { AuthContext } from './useAuth';

const CHAVE_FILA_OFFLINE = 'offlineTransactionsQueue';

/**
 * Provedor de Autenticação.
 *
 * @param {object} props - Propriedades do componente.
 * @param {React.ReactNode} props.children - Componentes filhos.
 * @returns {JSX.Element} O provedor de contexto.
 */
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [syncTrigger, setSyncTrigger] = useState(0);

  /**
   * Descobre se há uma sessão válida consultando o backend.
   *
   * @returns {Promise<object | null>} O perfil do usuário, ou null.
   */
  const carregarPerfil = useCallback(async () => {
    try {
      // `_sondagemDeSessao` avisa o interceptor de que um 401 aqui é a
      // resposta esperada para "ninguém logado", e não uma sessão expirada
      // que justifique renovar e redirecionar.
      const resposta = await api.get('/usuarios/me', { _sondagemDeSessao: true });
      setUser(resposta.data);
      return resposta.data;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    let ativo = true;

    carregarPerfil().finally(() => {
      if (ativo) setIsAuthLoading(false);
    });

    return () => {
      ativo = false;
    };
  }, [carregarPerfil]);

  /**
   * Sincroniza a fila de lançamentos feitos offline.
   *
   * Cada item é enviado individualmente e só sai da fila após confirmação. A
   * chave de idempotência, gerada quando o lançamento entrou na fila, garante
   * que um reenvio após queda de conexão não crie um débito duplicado.
   *
   * @returns {Promise<void>} Conclui após processar a fila.
   */
  const syncOfflineQueue = useCallback(async () => {
    const fila = JSON.parse(localStorage.getItem(CHAVE_FILA_OFFLINE) || '[]');
    if (fila.length === 0) return;

    const pendentes = [];
    let sincronizou = false;

    for (const item of fila) {
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
        // não resolve e manteria o item preso na fila para sempre.
        if (status && status >= 400 && status < 500 && status !== 429) {
          console.error('Lançamento offline descartado por ser inválido:', status);
          continue;
        }

        pendentes.push(item);
      }
    }

    if (pendentes.length > 0) {
      localStorage.setItem(CHAVE_FILA_OFFLINE, JSON.stringify(pendentes));
    } else {
      localStorage.removeItem(CHAVE_FILA_OFFLINE);
    }

    if (sincronizou) {
      setSyncTrigger((chave) => chave + 1);
    }
  }, []);

  useEffect(() => {
    if (!user) return undefined;

    if (navigator.onLine) {
      syncOfflineQueue();
    }

    window.addEventListener('online', syncOfflineQueue);
    return () => window.removeEventListener('online', syncOfflineQueue);
  }, [user, syncOfflineQueue]);

  /**
   * Autentica o usuário.
   *
   * Quando a conta tem segundo fator, nenhuma sessão é aberta: a função
   * devolve o token de desafio, que a interface usa na etapa seguinte.
   *
   * @param {string} username - O nome de usuário.
   * @param {string} password - A senha.
   * @returns {Promise<{ok: boolean, mfaRequerido?: boolean, desafio?: string, erro?: string}>}
   *   O desfecho da tentativa.
   */
  const login = async (username, password) => {
    const formulario = new URLSearchParams();
    formulario.append('username', username);
    formulario.append('password', password);

    try {
      const { data } = await api.post('/auth/login', formulario, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      if (data.mfa_requerido) {
        return { ok: true, mfaRequerido: true, desafio: data.token_de_desafio };
      }

      await carregarPerfil();
      return { ok: true, mfaRequerido: false };
    } catch (err) {
      return {
        ok: false,
        erro:
          err.response?.status === 429
            ? 'Muitas tentativas. Aguarde alguns minutos.'
            : 'Usuário ou senha incorretos.',
      };
    }
  };

  /**
   * Conclui o login informando o código do segundo fator.
   *
   * @param {string} desafio - O token de desafio recebido no login.
   * @param {string} codigo - O código TOTP ou de recuperação.
   * @returns {Promise<{ok: boolean, erro?: string}>} O desfecho da tentativa.
   */
  const verificarSegundoFator = async (desafio, codigo) => {
    try {
      await api.post('/auth/mfa/verificar', {
        token_de_desafio: desafio,
        codigo,
      });

      await carregarPerfil();
      return { ok: true };
    } catch (err) {
      return {
        ok: false,
        erro:
          err.response?.status === 429
            ? 'Muitas tentativas. Aguarde alguns minutos.'
            : 'Código inválido ou expirado.',
      };
    }
  };

  /**
   * Encerra a sessão e apaga todo dado financeiro local.
   *
   * @returns {Promise<void>} Conclui após a limpeza.
   */
  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // Mesmo que a chamada falhe, o estado local precisa ser limpo: manter a
      // sessão na tela por causa de um erro de rede seria pior.
    }

    localStorage.removeItem(CHAVE_FILA_OFFLINE);
    await limparCachesDaApi();

    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthLoading,
        syncTrigger,
        login,
        verificarSegundoFator,
        logout,
        recarregarPerfil: carregarPerfil,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

