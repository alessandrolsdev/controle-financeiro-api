// Arquivo: frontend/src/main.jsx
// (SUBSTITUA O SEU POR ESTE)

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';
import { AuthProvider } from './context/AuthContext';
import { BrowserRouter } from 'react-router-dom'; // 1. IMPORTE O ROUTER

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter> {/* 2. O ROUTER VEM PRIMEIRO */}
      <AuthProvider> {/* 3. O AUTH VEM DEPOIS */}
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);