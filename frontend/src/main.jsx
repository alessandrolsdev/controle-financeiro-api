// Arquivo: frontend/src/main.jsx
/*
 * Ponto de Entrada (Entrypoint) Principal da Aplicação React.
 *
 * Este arquivo é o "alicerce" do frontend. Sua responsabilidade é:
 * 1. Importar o React e o ReactDOM.
 * 2. Encontrar a 'div' com 'id="root"' no 'index.html'.
 * 3. Renderizar (montar) o componente principal '<App />' dentro dela.
 * 4. "Envelopar" (wrap) toda a aplicação com os 'Providers'
 * de estado global (AuthContext, ThemeContext), disponibilizando-os
 * para todos os componentes filhos.
 */

// Importações padrão do React
import React from 'react';
import ReactDOM from 'react-dom/client';

// Componentes principais da nossa aplicação
import App from './App.jsx'; // O Roteador principal
import { AuthProvider } from './context/AuthContext'; // O "Cérebro" de Login/Usuário
import { ThemeProvider } from './context/ThemeContext'; // O "Cérebro" de Tema (Light/Dark)

// Estilos globais (Design System) que afetam toda a aplicação
import './index.css';

// --- Inicialização do React (React 18+) ---

// 1. Encontra a <div id="root"> no 'index.html'.
// 2. Cria a "raiz" da aplicação React usando a API moderna (createRoot).
ReactDOM.createRoot(document.getElementById('root')).render(
  
  // <React.StrictMode> é um wrapper de desenvolvimento.
  // Ele nos ajuda a encontrar bugs e práticas obsoletas,
  // mas não é executado em produção (deploy).
  <React.StrictMode>
    
    {/*
      Esta é a "árvore de provedores" (Provider Tree).
      Ao envelopar o <App /> (que contém todas as páginas)
      com os Providers, garantimos que qualquer componente
      em qualquer nível possa acessar seus estados.
    */}
    
    {/* Fornece o estado de autenticação (token, user, login, logout)
      para toda a aplicação através do hook 'useAuth()'.
    */}
    <AuthProvider>
      
      {/* Fornece o estado de tema (theme, toggleTheme)
        e aplica a classe .light-mode/.dark-mode no body.
      */}
      <ThemeProvider>
        
        {/* O componente <App /> contém o 'BrowserRouter'
            e toda a lógica de roteamento. */}
        <App />
        
      </ThemeProvider>
    </AuthProvider>
    
  </React.StrictMode>,
);