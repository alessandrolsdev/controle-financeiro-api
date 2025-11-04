// Arquivo: frontend/vite.config.js
// Responsabilidade: Configurar o Vite, nosso servidor de desenvolvimento
// e ferramenta de "build" (compilação) do frontend.

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    // Plugin padrão para fazer o React (JSX) funcionar com o Vite.
    react(),
    
    // --- O Coração do Modo Offline ---
    // Este plugin transforma nosso site em um PWA "instalável".
    VitePWA({
      // 'autoUpdate' fará com que o app do usuário se atualize sozinho
      // no fundo, assim que publicarmos uma nova versão no Vercel.
      registerType: 'autoUpdate',
      
      // 'manifest': É a "carteira de identidade" do nosso app.
      // É o que diz ao celular "eu sou um app" e como me comportar.
      manifest: {
        name: 'NOMAD - Controle Financeiro', // Nome longo do app
        short_name: 'NOMAD', // Nome que aparece abaixo do ícone
        description: 'Aplicativo de controle financeiro para pequenas empresas.',
        theme_color: '#007bff', // Cor da barra de status no Android (nosso azul)
        background_color: '#ffffff', // Cor da tela de "splash"
        display: 'standalone', // Faz o app abrir em tela cheia, sem a barra do navegador
        scope: '/', // O escopo do app
        start_url: '/', // A página que abre ao iniciar o app
        
        // Ícones que aparecerão na tela inicial do celular
        icons: [
          {
            src: 'logo-192.png', // Ícone para Android
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'logo-512.png', // Ícone principal (maior resolução)
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
    })
  ],
})