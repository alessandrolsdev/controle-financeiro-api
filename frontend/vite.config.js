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
          runtimeCaching: [
            {
              // Intercepta requisições para a API base
              urlPattern: new RegExp(`^${env.VITE_API_BASE_URL}`),
              
              // Estratégia StaleWhileRevalidate: retorna do cache e atualiza em segundo plano
              handler: 'StaleWhileRevalidate',
              
              method: 'GET',
              
              options: {
                cacheName: 'api-cache-v1',
                
                cacheableResponse: {
                  statuses: [200],
                },
                
                expiration: {
                  maxEntries: 50,
                  maxAgeSeconds: 60 * 60 * 24 * 7,
                },
              },
            },
          ],
        },
      }),
    ],
  };
});
