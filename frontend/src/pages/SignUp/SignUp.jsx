// Arquivo: frontend/src/pages/SignUp/SignUp.jsx
/**
 * @file Página de Cadastro (SignUp).
 * @description Rota pública para registro de novos usuários.
 */

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios'; 
import './SignUp.css';
import logoNomad from '../../assets/logo.png';

/**
 * Componente de Cadastro.
 *
 * Permite que novos usuários criem uma conta fornecendo nome de usuário e senha.
 * Após o cadastro bem-sucedido, redireciona para a página de login.
 *
 * @returns {JSX.Element} A página de cadastro renderizada.
 */
function SignUp() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const navigate = useNavigate();

  /**
   * Manipula o envio do formulário de cadastro.
   *
   * Envia uma requisição POST para a API pública de criação de usuários.
   * Exibe mensagens de sucesso ou erro conforme a resposta.
   *
   * @param {Event} event - O evento de submit do formulário.
   */
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      await axios.post(`${import.meta.env.VITE_API_BASE_URL}/usuarios/`, {
        nome_usuario: username,
        senha: password,
      });

      setLoading(false);
      setSuccess('Conta criada com sucesso! Redirecionando para o login...');

      setTimeout(() => {
        navigate('/login');
      }, 2000);

    } catch (err) {
      setLoading(false);
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        console.error('Erro ao criar conta:', err);
        setError('Ocorreu um erro inesperado. Tente novamente.');
      }
    }
  };

  return (
    <div className="signup-page-wrapper">
      <div className="signup-container">
        
        <img src={logoNomad} alt="Logo NOMAD" className="signup-logo" />
        
        <h1 className="signup-title">Crie sua Conta</h1>
        <p className="signup-subtitle">Controle total, onde você estiver.</p>
        
        <form className="signup-form" onSubmit={handleSubmit}>
          
          {error && <p className="error-message">{error}</p>}
          {success && <p className="success-message">{success}</p>}

          <div className="input-group">
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Nome de usuário (ex: 'alessandro')"
              required
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
          
          <button type="submit" className="signup-button" disabled={loading}>
            {loading ? 'Criando...' : 'Criar Conta'}
          </button>

          <div className="signup-links">
            <Link to="/login" className="signup-link">
              Já tem uma conta? Faça o login
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
} 

export default SignUp;
