// Arquivo: frontend/vite.config.js

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      // O 'registerType' autoUpdate fará o app atualizar automaticamente
      // quando houver uma nova versão.
      registerType: 'autoUpdate',

      // O 'manifest' é o coração do PWA
      manifest: {
        name: 'NOMAD - Aplicativo de Controle Financeiro',
        short_name: 'NOMAD',
        description: 'Aplicativo de controle financeiro.',
        theme_color: '#007bff', // A cor principal do seu app
        background_color: '#ffffff',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        icons: [
          {
            src: 'logo-192.png', // O plugin vai criar este a partir do seu logo-512
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'logo-512.png', // O ícone principal que você criou
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
    })
  ],
})