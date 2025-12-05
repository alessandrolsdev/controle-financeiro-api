// Arquivo: frontend/src/App.jsx
/**
 * @file Componente Principal da Aplicação e Roteamento.
 * @description Gerencia a navegação da aplicação utilizando o React Router, definindo rotas públicas e protegidas.
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import MainLayout from './layouts/MainLayout';
import Login from './pages/Login/Login';
import Dashboard from './pages/Dashboard/Dashboard';
import Settings from './pages/Settings/Settings';
import SignUp from './pages/SignUp/SignUp';
import Profile from './pages/Profile/Profile';
import Reports from './pages/Reports/Reports';

/**
 * Componente raiz que define a estrutura de rotas da aplicação.
 *
 * Implementa verificação de autenticação:
 * - Redireciona usuários não autenticados para a tela de login.
 * - Redireciona usuários autenticados para o dashboard ao tentarem acessar login/signup.
 * - Exibe uma tela de carregamento enquanto verifica o estado da autenticação.
 *
 * @returns {JSX.Element} A árvore de rotas da aplicação.
 */
function App() {
  const { token, isAuthLoading } = useAuth();

  if (isAuthLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: '#0B1A33', color: 'white', fontFamily: 'Montserrat' }}>
        Carregando aplicação...
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* --- Rotas Públicas --- */}
        <Route
          path="/login"
          element={
            !token ? <Login /> : <Navigate to="/" replace />
          }
        />
        <Route
          path="/signup"
          element={
            !token ? <SignUp /> : <Navigate to="/" replace />
          }
        />

        {/* --- Rotas Protegidas --- */}
        <Route
          path="/"
          element={
            token ? <MainLayout /> : <Navigate to="/login" replace />
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
          <Route path="profile" element={<Profile />} />
        </Route>

        <Route path="*" element={<Navigate to={token ? "/" : "/login"} replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
