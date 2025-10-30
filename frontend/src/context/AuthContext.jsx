// Arquivo: frontend/src/context/AuthContext.jsx

import React, { createContext, useState, useContext } from 'react';
import axios from 'axios';

// 1. Cria o Contexto
const AuthContext = createContext();

// 2. Cria o "Provedor" (o componente que vai gerenciar o estado)
export const AuthProvider = ({ children }) => {
  // Guarda o token no estado. Inicialmente, tentamos pegar do localStorage.
  const [token, setToken] = useState(localStorage.getItem('token'));

  const login = async (username, password) => {
    // Formata os dados para o backend (como fizemos na página de Login)
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
      const response = await axios.post('http://127.0.0.1:8000/token', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      const newToken = response.data.access_token;
      setToken(newToken); // 1. Atualiza o estado
      localStorage.setItem('token', newToken); // 2. Salva no localStorage
      
      return true; // Sucesso

    } catch (err) {
      console.error('Erro no login (AuthContext):', err);
      return false; // Falha
    }
  };

  const logout = () => {
    setToken(null); // 1. Remove do estado
    localStorage.removeItem('token'); // 2. Remove do localStorage
  };

  // 3. Compartilha o token e as funções com todos os componentes "filhos"
  return (
    <AuthContext.Provider value={{ token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// 4. Cria um "hook" personalizado para facilitar o uso do contexto
export const useAuth = () => {
  return useContext(AuthContext);
};