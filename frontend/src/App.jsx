// Arquivo: frontend/src/App.jsx
// Responsabilidade: O "Guarda de Trânsito" (Roteador Principal) da Aplicação.
//
// Este componente tem uma única função:
// 1. "Ouvir" o nosso 'AuthContext' (para saber se o usuário está logado).
// 2. Controlar qual PÁGINA é exibida para o usuário com base na URL
//    e no status de login.

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext'; // Nosso "cérebro" de login

// Importa todas as nossas "Páginas" (os "cômodos" da casa)
import Login from './pages/Login/Login';
import Dashboard from './pages/Dashboard/Dashboard';
import Settings from './pages/Settings/Settings';

function App() {
  // Pega o 'token' do nosso cérebro global (AuthContext).
  // Se 'token' existir, o usuário está logado. Se for 'null', não está.
  const { token } = useAuth();

  return (
    // O 'BrowserRouter' ativa o roteamento.
    // O 'basename' é CRUCIAL para o deploy no Vercel/GitHub Pages,
    // garantindo que as rotas funcionem em subdiretórios.
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      
      {/* O 'Routes' é o "controlador de tráfego" que olha a URL */}
      <Routes>
        
        {/* --- Rota Pública: /login --- */}
        <Route 
          path="/login"
          element={
            // Lógica da Rota Pública:
            // SE o usuário NÃO tiver token, mostre a página de Login.
            // SE ele TIVER token, redirecione-o para o Dashboard (/).
            !token ? <Login /> : <Navigate to="/" />
          }
        />

        {/* --- Rotas Protegidas (Privadas) --- */}
        
        {/* Rota Principal: / (Dashboard) */}
        <Route 
          path="/"
          element={
            // Lógica da Rota Protegida:
            // SE o usuário TIVER token, mostre o Dashboard.
            // SE ele NÃO tiver token, "chute" ele para a página de /login.
            token ? <Dashboard /> : <Navigate to="/login" />
          } 
        />
        
        {/* Rota de Configurações: /settings */}
        <Route 
          path="/settings"
          element={
            // Lógica da Rota Protegida (igual à do Dashboard):
            // SE o usuário TIVER token, mostre a página de Configurações.
            // SE ele NÃO tiver token, "chute" ele para a página de /login.
            token ? <Settings /> : <Navigate to="/login" />
          } 
        />

      </Routes>
    </BrowserRouter>
  );
}

export default App;