// Arquivo: frontend/vite.config.js (VERSÃO REATORADA COM CACHE DE API)
// Responsabilidade: Configurar o Vite E o Service Worker (PWA).
//
// REATORAÇÃO (Frontend 1):
// Adicionamos a lógica 'workbox.runtimeCaching' para instruir
// o Service Worker a salvar em cache as respostas da nossa API (GET),
// permitindo que o app funcione (leia dados) mesmo offline.

// 1. Importamos 'defineConfig' E 'loadEnv' (NOVO)
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// 2. Convertemos 'export default' para uma FUNÇÃO (NOVO)
// Isso nos dá acesso à variável 'mode' (development ou production)
// e nos permite carregar os arquivos .env
export default defineConfig(({ mode }) => {
  
  // 3. Carrega o arquivo .env da raiz do frontend (NOVO)
  // O 'process.cwd()' aponta para a pasta 'frontend/'
  const env = loadEnv(mode, process.cwd(), '');

  // 4. Retornamos nosso objeto de configuração (NOVO)
  return {
    plugins: [
      // Plugin padrão para fazer o React (JSX) funcionar com o Vite.
      react(),
      
      // O Coração do Modo Offline
      VitePWA({
        // 'autoUpdate' fará com que o app do usuário se atualize sozinho
        registerType: 'autoUpdate',
        
        // 'manifest': A "carteira de identidade" do nosso app (SEM MUDANÇAS)
        manifest: {
          name: 'NOMAD - Controle Financeiro',
          short_name: 'NOMAD',
          description: 'Aplicativo de controle financeiro para pequenas empresas.',
          theme_color: '#007bff',
          background_color: '#ffffff',
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

        // --- 5. A GRANDE MUDANÇA: A "REDE DE SEGURANÇA" (NOVO) ---
        workbox: {
          // Define regras de cache para o 'runtime' (quando o app está rodando)
          runtimeCaching: [
            {
              // Intercepta todas as chamadas que COMEÇAM com a URL da nossa API
              // (lida do nosso .env, ex: 'http://127.0.0.1:8000')
              // A RegExp garante que estamos pegando a URL base.
              urlPattern: new RegExp(`^${env.VITE_API_BASE_URL}`),
              
              // A Estratégia: "Stale While Revalidate"
              // 1. (Stale) Sirva o dado do cache IMEDIATAMENTE.
              // 2. (While Revalidate) Em paralelo, busque na rede e atualize o cache.
              handler: 'StaleWhileRevalidate',
              
              // Apenas queremos salvar em cache requisições GET
              method: 'GET',
              
              options: {
                cacheName: 'api-cache-v1', // Nome do "compartimento" no cache
                
                cacheableResponse: {
                  statuses: [200], // Só salva em cache respostas de SUCESSO
                },
                
                expiration: {
                  maxEntries: 50, // Não guarda mais que 50 chamadas de API
                  maxAgeSeconds: 60 * 60 * 24 * 7, // Guarda por 7 dias
                },
              },
            },
          ],
        },
      }), // Fim do VitePWA
    ], // Fim dos plugins
  }; // Fim do objeto de retorno
}); // Fim do defineConfig