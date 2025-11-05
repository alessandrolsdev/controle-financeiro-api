// Arquivo: frontend/src/App.jsx
// (VERSÃO V3.0 - COMPLETA, COM TODAS AS ROTAS DA NAVBAR)

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

// --- O "Layout" (concha) para páginas protegidas ---
import MainLayout from './layouts/MainLayout';

// --- Nossas Páginas ---
import Login from './pages/Login/Login';
import Dashboard from './pages/Dashboard/Dashboard';
import Settings from './pages/Settings/Settings';
import SignUp from './pages/SignUp/SignUp'; // A NOVA PÁGINA QUE CRIAMOS

/**
 * Componente "Guarda de Trânsito" (Roteador Principal).
 * Ele controla qual página é exibida com base na URL e no status de login.
 */
function App() {
  const { token } = useAuth(); // Pega o token do "cérebro"

  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Routes>
        
        {/* --- Rotas Públicas (Telas Cheias, sem Navbar) --- */}
        
        {/* Rota 1: Login */}
        <Route 
          path="/login" 
          element={
            // Se NÃO tiver token, mostre o Login.
            // Se TIVER token, jogue o usuário para o Dashboard.
            !token ? <Login /> : <Navigate to="/" />
          } 
        />
        
        {/* Rota 2: Criar Nova Conta (SignUp) */}
        <Route 
          path="/signup" 
          element={
            // Mesma lógica do Login
            !token ? <SignUp /> : <Navigate to="/" />
          } 
        />
        
        {/* (Aqui poderíamos adicionar /forgot-password no futuro) */}


        {/* --- Rotas Protegidas (Dentro da "Concha" do MainLayout) --- */}
        
        {/* Esta é a "Rota Pai" protegida. 
            Se o usuário TIVER token, ele renderiza o <MainLayout />.
            Se NÃO tiver, ele é "chutado" para o /login. 
        */}
        <Route 
          path="/" 
          element={token ? <MainLayout /> : <Navigate to="/login" />}
        >
          {/* As rotas abaixo são "Filhas" e serão renderizadas
              dentro do <Outlet> do MainLayout */}

          {/* 'index' significa a rota pai ("/") */}
          <Route index element={<Dashboard />} /> 
          
          <Route path="settings" element={<Settings />} />
          
          {/* Rotas "Placeholder" para os links da Navbar */}
          {/* Elas ainda não têm uma página bonita, mas já funcionam! */}
          <Route path="reports" element={
            <div style={{ padding: '2rem' }}>
              <h1>Relatórios</h1>
              <p>(Página em construção...)</p>
            </div>
          } />
          
          <Route path="profile" element={
            <div style={{ padding: '2rem' }}>
              <h1>Perfil do Usuário</h1>
              <p>(Página em construção...)</p>
            </div>
          } />

        </Route>

      </Routes>
    </BrowserRouter>
  );
}

export default App;