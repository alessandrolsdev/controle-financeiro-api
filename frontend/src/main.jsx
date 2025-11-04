// Arquivo: frontend/src/main.jsx
// Responsabilidade: O PONTO DE ENTRADA (Entrypoint) da aplicação React.

// Importações padrão do React
import React from 'react';
import ReactDOM from 'react-dom/client';

// Componentes principais da nossa aplicação
import App from './App.jsx'; // O "Guarda de Trânsito" (Roteador)
import { AuthProvider } from './context/AuthContext'; // O "Cérebro" do Login

// Estilos globais que afetam toda a aplicação
import './index.css';

// --- Inicialização do React ---

// 1. Encontra a <div id="root"> no nosso arquivo 'index.html'.
// 2. Cria a "raiz" da aplicação React dentro dela.
ReactDOM.createRoot(document.getElementById('root')).render(
  
  // <React.StrictMode> é um ajudante de desenvolvimento.
  // Ele não faz nada em produção, mas nos avisa (no console) sobre
  // práticas ruins ou código obsoleto durante o desenvolvimento.
  <React.StrictMode>
    
    {/*
      Esta é a parte mais importante da nossa arquitetura de frontend.
      Ao "envelopar" o <App /> (que contém todas as nossas páginas)
      com o <AuthProvider>, nós garantimos que CADA componente
      dentro do <App> (Login, Dashboard, Modal, etc.) tenha acesso
      ao estado de autenticação (o token e as funções de login/logout)
      através do hook 'useAuth()'.
    */}
    <AuthProvider>
      <App />
    </AuthProvider>
    
  </React.StrictMode>,
);