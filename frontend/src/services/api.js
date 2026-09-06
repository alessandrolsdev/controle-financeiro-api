// Arquivo: frontend/src/services/api.js
/**
 * @file Cliente HTTP Centralizado (Axios).
 * @description Instância configurada para autenticação por cookie httpOnly,
 * com proteção CSRF e renovação automática de sessão.
 *
 * Mudança em relação à versão anterior: o token deixou de ficar em
 * `localStorage`, onde qualquer script na página — inclusive o injetado por um
 * XSS — conseguia lê-lo e exfiltrá-lo. Agora ele viaja em um cookie httpOnly
 * que o JavaScript não alcança.
 *
 * Como o navegador envia cookies automaticamente, isso reintroduz o risco de
 * CSRF. A defesa é o padrão double-submit: o servidor grava um token CSRF em um
 * cookie legível, e este cliente o ecoa no cabeçalho `X-CSRF-Token`. Um site
 * atacante consegue disparar a requisição, mas não consegue ler o cookie de
 * outro domínio para preencher o cabeçalho.
 */

import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  // Necessário para que os cookies de sessão sejam enviados em requisições
  // de origem cruzada (frontend e API em domínios distintos).
  withCredentials: true,
});

/**
 * Lê um cookie pelo nome.
 *
 * @param {string} nome - O nome do cookie.
 * @returns {string | null} O valor, ou null se ausente.
 */
const lerCookie = (nome) => {
  const encontrado = document.cookie
    .split('; ')
    .find((linha) => linha.startsWith(`${nome}=`));

  return encontrado ? decodeURIComponent(encontrado.split('=')[1]) : null;
};

/**
 * Localiza o cookie CSRF, com ou sem o prefixo `__Host-`.
 *
 * O backend usa o prefixo `__Host-` em produção (onde há HTTPS) e o omite em
 * desenvolvimento, então o cliente precisa aceitar as duas formas.
 *
 * @returns {string | null} O token CSRF atual.
 */
const obterTokenCsrf = () =>
  lerCookie('__Host-nomad_csrf') ?? lerCookie('nomad_csrf');

const METODOS_INSEGUROS = ['post', 'put', 'patch', 'delete'];

api.interceptors.request.use(
  (config) => {
    if (METODOS_INSEGUROS.includes((config.method || '').toLowerCase())) {
      const csrf = obterTokenCsrf();
      if (csrf) {
        config.headers['X-CSRF-Token'] = csrf;
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

/**
 * Remove os caches de resposta da API gravados por versões antigas do PWA.
 *
 * Versões anteriores armazenavam saldos e extrato no Cache Storage por até
 * sete dias. A configuração foi removida, mas as entradas já gravadas
 * permanecem no disco de quem tem o app instalado até serem apagadas.
 *
 * @returns {Promise<void>} Conclui quando os caches tiverem sido removidos.
 */
export const limparCachesDaApi = async () => {
  if (typeof caches === 'undefined') return;

  try {
    const nomes = await caches.keys();
    await Promise.all(
      nomes
        .filter((nome) => nome.startsWith('api-cache'))
        .map((nome) => caches.delete(nome))
    );
  } catch (err) {
    console.warn('Falha ao limpar caches da API:', err);
  }
};

/*
 * Renovação automática de sessão.
 *
 * O token de acesso dura 15 minutos. Em vez de deslogar o usuário no meio de
 * uma tarefa, uma resposta 401 dispara uma tentativa de renovação e a
 * requisição original é repetida.
 *
 * A promessa de renovação é compartilhada: se cinco requisições receberem 401
 * ao mesmo tempo, uma única chamada a /auth/refresh é feita. Sem isso, as
 * cinco rotacionariam o refresh token em paralelo e quatro delas seriam
 * interpretadas pelo servidor como reuso — derrubando a sessão inteira.
 */
let renovacaoEmAndamento = null;

/**
 * Renova a sessão, reaproveitando a chamada já em andamento se houver.
 *
 * @returns {Promise<boolean>} True se a sessão foi renovada.
 */
const renovarSessao = () => {
  if (!renovacaoEmAndamento) {
    renovacaoEmAndamento = api
      .post('/auth/refresh')
      .then(() => true)
      .catch(() => false)
      .finally(() => {
        renovacaoEmAndamento = null;
      });
  }

  return renovacaoEmAndamento;
};

/** Rotas cujo 401 é a resposta esperada e não deve disparar renovação. */
const ROTAS_DE_AUTENTICACAO = ['/auth/login', '/auth/refresh', '/auth/mfa/verificar'];

/** Páginas onde estar deslogado é o estado normal. */
const PAGINAS_PUBLICAS = ['/login', '/signup'];

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const requisicao = error.config;
    const status = error.response?.status;

    const podeRenovar =
      status === 401 &&
      requisicao &&
      !requisicao._jaTentouRenovar &&
      // Uma sondagem de sessão (a checagem inicial de "existe alguém logado?")
      // recebe 401 como resposta legítima. Sem esta exceção, abrir a tela de
      // login dispara renovação, falha e redireciona para /login de novo —
      // um laço infinito de navegação.
      !requisicao._sondagemDeSessao &&
      !ROTAS_DE_AUTENTICACAO.some((rota) => requisicao.url?.includes(rota));

    if (podeRenovar) {
      requisicao._jaTentouRenovar = true;

      if (await renovarSessao()) {
        return api(requisicao);
      }

      // A renovação falhou: a sessão acabou de fato.
      await limparCachesDaApi();

      // Redirecionar estando já em uma página pública recarregaria a tela em
      // laço.
      if (!PAGINAS_PUBLICAS.includes(window.location.pathname)) {
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default api;
