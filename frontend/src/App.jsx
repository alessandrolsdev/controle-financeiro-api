// Arquivo: frontend/src/App.jsx (Versão Final com Roteamento)

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Login from './pages/Login/Login';
import Dashboard from './pages/Dashboard/Dashboard';

function App() {
  const { token } = useAuth(); // Pega o token do nosso "cérebro"

  return (
    <BrowserRouter>
      <Routes>
        {/* Rota 1: A Página de Login */}
        <Route 
          path="/login" 
          element={!token ? <Login /> : <Navigate to="/" />} 
        />
        
        {/* Rota 2: A Página Principal (Dashboard) */}
        <Route 
          path="/" 
          element={token ? <Dashboard /> : <Navigate to="/login" />} 
        />
      </Routes>
    </BrowserRouter>
  );
}
// Lógica de roteamento:
// - Se o usuário for para "/login" E NÃO tiver token, mostre o Login.
// - Se o usuário for para "/login" E TIVER token, redirecione para "/".
// - Se o usuário for para "/" E TIVER token, mostre o Dashboard.
// - Se o usuário for para "/" E NÃO tiver token, redirecione para "/login".

export default App;