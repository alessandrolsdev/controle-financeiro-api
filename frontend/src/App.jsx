import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Login from './pages/Login/Login';
import Dashboard from './pages/Dashboard/Dashboard';
import Settings from './pages/Settings/Settings';
import RegistrarTransacao from './pages/RegistrarTransacao/RegistrarTransacao';

function App() {
  const { isAuthenticated } = useAuth(); 

  // O <BrowserRouter> foi REMOVIDO daqui
  return (
    <Routes>
      <Route
        path="/login"
        element={!isAuthenticated ? <Login /> : <Navigate to="/" />}
      />
      <Route
        path="/"
        element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />}
      />
      <Route 
        path="/settings" 
        element={isAuthenticated ? <Settings /> : <Navigate to="/login" />} 
      />
      <Route 
        path="/registrar-gasto" 
        element={isAuthenticated ? <RegistrarTransacao /> : <Navigate to="/login" />} 
      />
    </Routes>
  );
}

export default App;