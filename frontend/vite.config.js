// Arquivo: frontend/vite.config.js
/*
 * Arquivo de Configuração do Vite (O "Construtor" do Frontend).
 *
 * Este arquivo define como o Vite (nossa ferramenta de build)
 * deve compilar e otimizar nosso projeto React.
 *
 * Responsabilidades:
 * 1. Habilitar o React (plugin-react).
 * 2. Configurar o 'vite-plugin-pwa' para transformar o site
 * em um Progressive Web App (PWA) instalável.
 * 3. Gerar o 'manifest.webmanifest' (a "identidade" do PWA).
 * 4. Configurar a estratégia de cache 'StaleWhileRevalidate'
 * para nossas rotas de API, permitindo que o app
 * leia dados (GET) mesmo quando estiver offline.
 */

// 1. Importa 'defineConfig' E 'loadEnv' (necessário para ler o .env)
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// Converte 'export default' para uma função para acessar 'mode'
export default defineConfig(({ mode }) => {
  
  // Carrega as variáveis de ambiente (ex: VITE_API_BASE_URL)
  // do arquivo '.env' na pasta 'frontend/'
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [
      // Plugin padrão para fazer o React (JSX) funcionar
      react(),
      
      // --- O Coração do Modo Offline (PWA) ---
      VitePWA({
        // 'autoUpdate' faz o app do usuário se atualizar sozinho
        // em segundo plano quando publicamos uma nova versão.
        registerType: 'autoUpdate',
        
        // 'manifest': A "carteira de identidade" do app.
        // (Define nome, ícones, cores, etc., para instalação)
        manifest: {
          name: 'NOMAD - Controle Financeiro', // Nome longo
          short_name: 'NOMAD', // Nome abaixo do ícone
          description: 'Aplicativo de controle financeiro para pequenas empresas.',
          theme_color: '#0B1A33', // Cor (Azul Guardião) da barra no Android
          background_color: '#0B1A33', // Cor da tela de "splash"
          display: 'standalone', // Faz o app abrir em tela cheia (sem barra do navegador)
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

        // --- A "Rede de Segurança" Offline (V-Revert 1) ---
        // Configura o 'Workbox' (o Service Worker) para
        // salvar em cache as respostas da nossa API.
        workbox: {
          runtimeCaching: [
            {
              // Intercepta todas as chamadas que COMEÇAM com a URL
              // da nossa API (ex: 'https://...onrender.com')
              urlPattern: new RegExp(`^${env.VITE_API_BASE_URL}`),
              
              // A Estratégia: "Stale While Revalidate"
              // 1. (Stale) Sirva o dado do cache IMEDIATAMENTE.
              // 2. (While Revalidate) Em paralelo, busque na rede e atualize o cache
              //    para a próxima visita.
              handler: 'StaleWhileRevalidate',
              
              // Aplica esta regra APENAS a requisições 'GET'
              method: 'GET',
              
              options: {
                cacheName: 'api-cache-v1', // Nome do "compartimento" no cache
                
                cacheableResponse: {
                  statuses: [200], // Só salva em cache respostas de SUCESSO (200 OK)
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