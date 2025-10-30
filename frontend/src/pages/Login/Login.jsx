// Arquivo: frontend/src/pages/Login/Login.jsx (Versão Completa e Corrigida)

import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom'; // Importa o hook de navegação
import './Login.css';

function Login() { 
  
  // --- Hooks (preparação) ---
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate(); // Prepara a função de navegação

  // --- Função de Envio ---
  const handleSubmit = async (event) => { // <-- CHAVE DO HANDLESUBMIT ABRE
    event.preventDefault();
    setError('');

    try { // <-- CHAVE DO TRY ABRE
      const success = await login(username, password);

      if (success) {
        console.log("LOGIN BEM-SUCEDIDO! Redirecionando...");
        navigate('/'); // Redireciona para o Dashboard (rota principal)
      } else {
        setError('Nome de usuário ou senha incorretos.');
      }
    } catch (err) { // <-- CHAVE DO CATCH ABRE
      console.error('Erro no handleSubmit do Login:', err);
      setError('Ocorreu um erro inesperado.');
    } // <-- CHAVE DO CATCH FECHA
  }; // <-- CHAVE DO HANDLESUBMIT FECHA

  // --- Renderização do JSX ---
  return (
    <div className="login-container">
      <form className="login-form" onSubmit={handleSubmit}>
        <h2>Login</h2>
        
        {error && <p className="error-message">{error}</p>}

        <div className="input-group">
          <label htmlFor="username">Usuário</label>
          <input
            type="text"
            id="username"
            placeholder="Digite seu usuário"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        <div className="input-group">
          <label htmlFor="password">Senha</label>
          <input
            type="password"
            id="password"
            placeholder="Digite sua senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit" className="login-button">
          Entrar
        </button>
      </form>
    </div>
  );

} 

export default Login;