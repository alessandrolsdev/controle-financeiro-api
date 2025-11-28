// Arquivo: frontend/src/App.jsx
/*
 * Componente Principal de Roteamento.
 *
 * Gerencia a navegação da aplicação utilizando 'react-router-dom'.
 * Implementa controle de acesso para Rotas Públicas e Protegidas.
 *
 * Estrutura:
 * 1. Rotas Públicas (/login, /signup): Acessíveis apenas para usuários não autenticados.
 * 2. Rotas Protegidas (/, /reports, etc): Exigem autenticação válida.
 *    Renderizadas dentro do MainLayout.
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
// Contexto de autenticação
import { useAuth } from './context/AuthContext';

// --- O "Layout" (a "concha") para páginas protegidas ---
import MainLayout from './layouts/MainLayout';

// Páginas da aplicação
import Login from './pages/Login/Login';
import Dashboard from './pages/Dashboard/Dashboard';
import Settings from './pages/Settings/Settings';
import SignUp from './pages/SignUp/SignUp';
import Profile from './pages/Profile/Profile';
import Reports from './pages/Reports/Reports';

function App() {
  // Obtém estado de autenticação
  const { token, isAuthLoading } = useAuth();

  /*
   * Aguarda a verificação inicial da autenticação antes de renderizar
   * para evitar redirecionamentos incorretos ou "flicker" de tela.
   */
  if (isAuthLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: '#0B1A33', color: 'white', fontFamily: 'Montserrat' }}>
        Carregando aplicação...
      </div>
    );
  }

  return (
    // 'BrowserRouter' ativa o roteamento no app
    <BrowserRouter>
      {/* 'Routes' funciona como um 'switch' para as rotas */}
      <Routes>

        {/* --- Rotas Públicas --- */}

        {/* Rota 1: Login */}
        <Route
          path="/login"
          element={
            // Redireciona para dashboard se já estiver autenticado
            !token ? <Login /> : <Navigate to="/" replace />
          }
        />

        {/* Rota 2: Criar Nova Conta (SignUp) */}
        <Route
          path="/signup"
          element={
            // Mesma lógica do Login
            !token ? <SignUp /> : <Navigate to="/" replace />
          }
        />

        {/* (Aqui poderíamos adicionar /forgot-password no futuro) */}


        {/* --- Rotas Protegidas --- */}

        {/* 
          Rota pai para áreas autenticadas.
          Renderiza MainLayout que contém a estrutura comum (Navbar, etc).
        */}
        <Route
          path="/"
          element={
            // Exige token para acesso, caso contrário redireciona para login
            token ? <MainLayout /> : <Navigate to="/login" replace />
          }
        >
          {/* 'index' define o componente padrão para a rota pai ("/") */}
          <Route index element={<Dashboard />} />

          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
          <Route path="profile" element={<Profile />} />

        </Route>

        {/* (Opcional: Uma rota "catch-all" 404) */}
        <Route path="*" element={<Navigate to={token ? "/" : "/login"} replace />} />

      </Routes>
    </BrowserRouter>
  );
}

export default App;