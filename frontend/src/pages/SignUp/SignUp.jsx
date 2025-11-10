// Arquivo: frontend/src/pages/SignUp/SignUp.jsx
/*
 * Página de Cadastro (Sign Up).
 *
 * Esta é uma rota pública (veja 'App.jsx') para que
 * novos usuários possam se registrar.
 *
 * Responsabilidades:
 * 1. Renderizar o formulário de cadastro (usuário, senha).
 * 2. Chamar o endpoint PÚBLICO 'POST /usuarios/' (usando 'axios' direto).
 * 3. Gerenciar o estado local do formulário (loading, error, success).
 * 4. Navegar para o '/login' após o sucesso.
 */

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
/*
 * Decisão de Engenharia:
 * Usamos 'axios' direto, pois esta é uma chamada PÚBLICA.
 * O nosso 'api.js' (interceptador) só funciona para
 * rotas autenticadas (que precisam de token).
 */
import axios from 'axios'; 
import './SignUp.css';
import logoNomad from '../../assets/logo.png';

function SignUp() {
  // --- Estados do Formulário ---
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  
  // --- Estados de Feedback (UI) ---
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(''); // Para a mensagem "Conta criada!"
  
  const navigate = useNavigate();

  /**
   * Lida com o envio do formulário de cadastro.
   */
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      // 1. Chama o endpoint PÚBLICO de criação de usuário
      // (Lê a URL da API diretamente do '.env' do Vite)
      await axios.post(`${import.meta.env.VITE_API_BASE_URL}/usuarios/`, {
        nome_usuario: username,
        senha: password,
      });

      // 2. SUCESSO!
      setLoading(false);
      setSuccess('Conta criada com sucesso! Redirecionando para o login...');

      // 3. Espera 2 segundos (para o usuário ler a msg)
      //    e redireciona para o Login.
      setTimeout(() => {
        navigate('/login');
      }, 2000);

    } catch (err) {
      // 4. ERRO!
      setLoading(false);
      if (err.response && err.response.data && err.response.data.detail) {
        // Pega o erro bonito da nossa API (ex: "Nome de usuário já registrado")
        setError(err.response.data.detail);
      } else {
        // (Erro de rede, ex: API "dormindo" no Render)
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
          
          {/* Mensagens de Feedback */}
          {error && <p className="error-message">{error}</p>}
          {success && <p className="success-message">{success}</p>}

          <div className="input-group">
            {/* (V4.0) Input com estilo "underline" */}
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