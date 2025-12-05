// Arquivo: frontend/src/pages/Login/Login.jsx
/**
 * @file Página de Login.
 * @description Rota pública para autenticação de usuários. Contém o formulário de login e redireciona para o dashboard após sucesso.
 */

import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import './Login.css';

import logoNomad from '../../assets/logo.png'; 

/**
 * Componente de Login.
 *
 * Permite que o usuário insira suas credenciais (nome de usuário e senha) para acessar a aplicação.
 * Utiliza o contexto de autenticação para realizar a operação de login.
 *
 * @returns {JSX.Element} A página de login renderizada.
 */
function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login } = useAuth(); 
  const navigate = useNavigate(); 

  /**
   * Manipula o envio do formulário de login.
   *
   * Chama a função de login do contexto. Se bem-sucedido, redireciona para a página inicial.
   * Caso contrário, exibe mensagem de erro.
   *
   * @param {Event} event - O evento de submit do formulário.
   */
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      const success = await login(username, password);

      if (success) {
        navigate('/'); 
      } else {
        setError('Nome de usuário ou senha incorretos.');
        setLoading(false);
      }
    } catch (err) {
      console.error('Erro no handleSubmit do Login:', err);
      setError('Ocorreu um erro inesperado. Tente novamente.');
      setLoading(false);
    }
  };

  return (
    <div className="login-page-wrapper">
      <div className="login-container">

        <img src={logoNomad} alt="Logo NOMAD" className="login-logo" />

        <h1 className="login-title">NOMAD</h1>
        <p className="login-subtitle">Offline. Sempre. Seu.</p>

        <form className="login-form" onSubmit={handleSubmit}>

          {error && <p className="error-message">{error}</p>}

          <div className="input-group">
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Nome de usuário"
              required
              autoCapitalize="none"
            />
          </div>

          <div className="input-group">
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Senha"
              required
            />
          </div>

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Entrando...' : 'ENTRAR'}
          </button>

          <div className="login-links">
            <Link to="/signup" className="login-link">Criar nova conta</Link>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Login;
