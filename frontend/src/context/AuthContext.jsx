// Arquivo: frontend/src/context/AuthContext.jsx
// Responsabilidade: O "Cérebro" de Autenticação Global.
//
// Este é o "Provedor de Contexto" (Context Provider) do React.
// Sua função é gerenciar o estado de autenticação (o token JWT)
// e fornecer as funções de 'login' e 'logout' para
// QUALQUER componente da aplicação que as solicite.
//
// É "envelopado" em volta do App no 'main.jsx'.

import React, { createContext, useState, useContext } from 'react';
import axios from 'axios';

// 1. Cria o "molde" do contexto
const AuthContext = createContext();

/**
 * Componente "Provedor" que envolve toda a aplicação.
 * Ele 'provê' (disponibiliza) o valor do token e as funções de login/logout
 * para todos os seus componentes "filhos" (todo o App).
 */
export const AuthProvider = ({ children }) => {
  
  // --- 1. O ESTADO (O "Crachá") ---
  
  // Inicializa o estado 'token'
  // 1º: Tenta ler o token do localStorage (para "lembrar" do usuário)
  // 2º: Se não houver nada, começa como 'null'.
  const [token, setToken] = useState(localStorage.getItem('token'));

  // --- 2. A AÇÃO DE LOGIN ---
  
  /**
   * Tenta autenticar o usuário no backend.
   * Se for bem-sucedido, salva o token no estado e no localStorage.
   * @param {string} username - O nome de usuário.
   * @param {string} password - A senha em texto plano.
   * @returns {boolean} - True se o login foi bem-sucedido, False se falhou.
   */
  const login = async (username, password) => {
    
    // O backend (OAuth2PasswordRequestForm) espera dados de "formulário",
    // não JSON. Por isso, usamos URLSearchParams.
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
      // --- A CORREÇÃO DE BUG ESTÁ AQUI ---
      // Usamos a variável de ambiente para que a URL seja
      // 'http://127.0.0.1:8000' em desenvolvimento local e
      // 'https://...onrender.com' em produção.
      const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/token`, formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      // Se a API retornou 200 OK, pegamos o token
      const newToken = response.data.access_token;
      
      // 1. Salva o token no estado do React (para o app reagir agora)
      setToken(newToken);
      // 2. Salva o token no localStorage (para "lembrar" do login se o usuário fechar o navegador)
      localStorage.setItem('token', newToken); 
      
      return true; // Sucesso

    } catch (err) {
      // Se a API retornar 401 (senha errada) ou qualquer outro erro...
      console.error('Erro no login (AuthContext):', err);
      return false; // Falha
    }
  };

  // --- 3. A AÇÃO DE LOGOUT ---
  
  /**
   * Desloga o usuário, limpando o token do estado e do localStorage.
   */
  const logout = () => {
    // 1. Remove o token do estado (o app vai reagir e redirecionar para /login)
    setToken(null);
    // 2. Remove o token do "lembrar"
    localStorage.removeItem('token');
  };

  // 4. COMPARTILHANDO OS DADOS
  // O 'value' é o objeto que será compartilhado com todos os componentes filhos.
  return (
    <AuthContext.Provider value={{ token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// --- 5. O "HOOK" CUSTOMIZADO (O Atalho) ---

/**
 * Este é um "Hook" customizado. É um atalho profissional.
 * Em vez de cada componente ter que importar 'useContext' e 'AuthContext',
 * eles podem simplesmente chamar 'useAuth()'.
 * * Ex: const { token, login } = useAuth();
 */
export const useAuth = () => {
  return useContext(AuthContext);
};