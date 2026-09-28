// Arquivo: frontend/src/App.jsx
/**
 * @file Componente Principal e Roteamento.
 * @description Define as rotas públicas e protegidas da aplicação.
 */

import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { useAuth } from './context/useAuth';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard/Dashboard';
import Login from './pages/Login/Login';
import Profile from './pages/Profile/Profile';
import Reports from './pages/Reports/Reports';
import Settings from './pages/Settings/Settings';
import SignUp from './pages/SignUp/SignUp';

/**
 * Componente raiz da aplicação.
 *
 * A autenticação é decidida pela presença de um perfil carregado — e não por
 * um token em `localStorage`, já que a sessão agora vive em cookies httpOnly
 * inacessíveis ao JavaScript.
 *
 * @returns {JSX.Element} A árvore de rotas.
 */
function App() {
  const { user, isAuthLoading } = useAuth();

  if (isAuthLoading) {
    return <div className="carregando">Carregando…</div>;
  }

  const autenticado = Boolean(user);

  return (
    <BrowserRouter>
      <Routes>
        {/* --- Rotas públicas --- */}
        <Route
          path="/login"
          element={!autenticado ? <Login /> : <Navigate to="/" replace />}
        />
        <Route
          path="/signup"
          element={!autenticado ? <SignUp /> : <Navigate to="/" replace />}
        />

        {/* --- Rotas protegidas --- */}
        <Route
          path="/"
          element={autenticado ? <MainLayout /> : <Navigate to="/login" replace />}
        >
          <Route index element={<Dashboard />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
          <Route path="profile" element={<Profile />} />
        </Route>

        <Route
          path="*"
          element={<Navigate to={autenticado ? '/' : '/login'} replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
