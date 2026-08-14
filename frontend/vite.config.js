// Arquivo: frontend/vite.config.js
/**
 * @file Configuração do Vite (Frontend Build Tool).
 * @description Define a configuração para compilação do React, geração do PWA e estratégias de cache offline.
 */

import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

/**
 * Exporta a configuração do Vite.
 * Utiliza o modo (desenvolvimento/produção) para carregar as variáveis de ambiente corretas.
 */
export default defineConfig(({ mode }) => {
  
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [
      react(),
      
      /**
       * Configuração do VitePWA para funcionalidade offline e instalação.
       *
       * Define o manifesto da aplicação (nome, ícones, cores) e configura o Workbox
       * para interceptar requisições de API e armazená-las em cache (StaleWhileRevalidate).
       */
      VitePWA({
        registerType: 'autoUpdate',
        
        manifest: {
          name: 'NOMAD - Controle Financeiro',
          short_name: 'NOMAD',
          description: 'Aplicativo de controle financeiro para pequenas empresas.',
          theme_color: '#0B1A33',
          background_color: '#0B1A33',
          display: 'standalone',
          scope: '/',
          start_url: '/', 
          icons: [
            {
              src: 'logo-192.png',
              sizes: '192x192',
              type: 'image/png',
            },
            {
              src: 'logo-512.png',
              sizes: '512x512',
              type: 'image/png',
            },
          ],
        },

        workbox: {
          /*
           * O cache em tempo de execução da API foi REMOVIDO deliberadamente.
           *
           * A configuração anterior guardava as respostas autenticadas da API
           * (saldos, extrato, transações) no Cache Storage por 7 dias, em disco
           * e em texto claro. Isso significava que:
           *
           *  - os dados financeiros sobreviviam ao logout, ficando acessíveis a
           *    qualquer pessoa com acesso ao dispositivo ou ao perfil do
           *    navegador;
           *  - em um computador compartilhado, o próximo usuário podia ver o
           *    extrato do anterior;
           *  - a estratégia StaleWhileRevalidate podia exibir saldos
           *    desatualizados como se fossem atuais.
           *
           * O app continua instalável e funcionando offline para o "casco"
           * (HTML, JS, CSS, ícones), que é o que o precache abaixo cobre. Os
           * lançamentos feitos offline continuam indo para a fila local e são
           * sincronizados quando a conexão volta.
           */
          globPatterns: ['**/*.{js,css,html,ico,png,svg,webmanifest}'],

          // Nunca intercepta chamadas à API, nem para responder do cache.
          navigateFallbackDenylist: [/^\/api\//],

          // Remove caches de versões anteriores do app — inclusive o
          // 'api-cache-v1' com dados financeiros de instalações antigas.
          cleanupOutdatedCaches: true,
          clientsClaim: true,
          skipWaiting: true,
        },
      }),
    ],
  };
});
