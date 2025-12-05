// Arquivo: frontend/src/main.jsx
/**
 * @file Ponto de entrada principal da aplicação React.
 * @description Inicializa a árvore de componentes, configura os provedores de contexto globais (Auth e Theme) e monta a aplicação no DOM.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';

import App from './App.jsx';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';

import './index.css';

/**
 * Inicializa a raiz da aplicação React e renderiza a árvore de componentes dentro dos provedores de contexto e StrictMode.
 */
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </AuthProvider>
  </React.StrictMode>,
);
