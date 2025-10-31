// Arquivo: frontend/src/context/AuthContext.js
// (SUBSTITUA O SEU POR ESTE)

import React, { createContext, useContext, useState } from 'react';
import api from '../services/api'; // Importa o 'api.js'

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('authToken'));

  const login = async (username, password) => {
    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);

      const response = await api.post('/token', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (response.data && response.data.access_token) {
        // A LINHA MAIS IMPORTANTE:
        localStorage.setItem('authToken', response.data.access_token);
        setIsAuthenticated(true);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Erro na função login (AuthContext):', error);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('authToken');
    setIsAuthenticated(false);
  };

  const value = { isAuthenticated, login, logout };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  return useContext(AuthContext);
};