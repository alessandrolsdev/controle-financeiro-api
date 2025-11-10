// Arquivo: frontend/src/App.jsx
"""
Componente Principal de Roteamento (O "Guarda de Trânsito").

Este componente é o "controlador" de navegação da aplicação.
Ele usa o 'react-router-dom' para definir todas as rotas
e implementa a lógica de Rota Pública vs. Rota Protegida.

Arquitetura de Roteamento:
1. Rotas Públicas (/login, /signup):
   - Acessíveis apenas se o usuário NÃO estiver logado.
   - Se um usuário logado tentar acessá-las, ele é redirecionado
     para o Dashboard ('/').
2. Rotas Protegidas (/, /reports, /settings, /profile):
   - Acessíveis apenas se o usuário ESTIVER logado (tiver um token).
   - Se um usuário deslogado tentar acessá-las, ele é redirecionado
     para o '/login'.
   - Elas são "aninhadas" dentro do <MainLayout />, que
     fornece a Navbar e os dados globais (filtros).
"""

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
// Importa o "cérebro" de autenticação
import { useAuth } from './context/AuthContext'; 

// --- O "Layout" (a "concha") para páginas protegidas ---
import MainLayout from './layouts/MainLayout';

// --- Nossas Páginas (os "cômodos") ---
import Login from './pages/Login/Login';
import Dashboard from './pagesS/Dashboard/Dashboard';
import Settings from './pages/Settings/Settings';
import SignUp from './pages/SignUp/SignUp';
import Profile from './pages/Profile/Profile';
import Reports from './pages/Reports/Reports';

function App() {
  // Pega o 'token' e o estado 'isAuthLoading' do "cérebro" (AuthContext)
  const { token, isAuthLoading } = useAuth();

  // Decisão de Arquitetura (V7.6 - Correção de Race Condition):
  // NÃO renderiza nada até que o AuthContext tenha
  // verificado o token. Isso impede que um usuário logado
  // veja a tela de login por 1 segundo (o "flash").
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
        
        {/* --- Rotas Públicas (Telas Cheias, sem Navbar) --- */}
        
        {/* Rota 1: Login */}
        <Route 
          path="/login" 
          element={
            // Se NÃO tiver token, mostre o Login.
            // Se TIVER token, redireciona para o Dashboard.
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


        {/* --- Rotas Protegidas (Dentro da "Concha" do MainLayout) --- */}
        
        {/* Esta é a "Rota Pai" protegida. 
          Ela usa o <MainLayout /> como seu 'element'.
          Todas as rotas filhas (abaixo) serão renderizadas
          dentro do <Outlet /> do MainLayout.
        */}
        <Route 
          path="/" 
          element={
            // Se TIVER token, renderiza o Layout (que contém as páginas).
            // Se NÃO tiver, redireciona para o /login.
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