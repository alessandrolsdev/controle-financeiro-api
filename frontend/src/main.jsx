// Arquivo: frontend/src/main.jsx (Versão Atualizada)

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';
import { AuthProvider } from './context/AuthContext'; // 1. Importa o Provedor

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {/* 2. "Envelopa" o <App /> com o <AuthProvider /> */}
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>,
);