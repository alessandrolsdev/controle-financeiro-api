// Arquivo: frontend/src/main.jsx
/*
 * Ponto de Entrada da Aplicação React.
 *
 * Responsável pela inicialização da árvore de componentes,
 * configuração dos Providers globais (Auth, Theme) e
 * montagem na DOM.
 */

// Importações padrão do React
import React from 'react';
import ReactDOM from 'react-dom/client';

// Componentes principais da nossa aplicação
import App from './App.jsx';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';

// Estilos globais
import './index.css';

// --- Inicialização do React (React 18+) ---

// Inicialização da raiz React
ReactDOM.createRoot(document.getElementById('root')).render(

  // StrictMode para verificações de desenvolvimento
  <React.StrictMode>

    {/* Configuração dos Provedores de Contexto Globais */}

    <AuthProvider>

      <ThemeProvider>

        <App />

      </ThemeProvider>
    </AuthProvider>

  </React.StrictMode>,
);