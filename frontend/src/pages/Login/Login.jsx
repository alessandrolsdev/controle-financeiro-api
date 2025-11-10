// Arquivo: frontend/src/pages/Login/Login.jsx
/*
 * Página de Login.
 *
 * Esta é uma rota pública (veja 'App.jsx') renderizada se
 * o usuário NÃO estiver autenticado.
 *
 * Responsabilidades:
 * 1. Renderizar o formulário de login (usuário, senha).
 * 2. Chamar a função 'login()' do 'AuthContext' (useAuth).
 * 3. Gerenciar o estado local do formulário (loading, error).
 * 4. Navegar para o Dashboard ('/') em caso de sucesso.
 */

import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext'; // O "cérebro"
import { useNavigate, Link } from 'react-router-dom';
import './Login.css'; // Estilos locais

// Importa o logo
import logoNomad from '../../assets/logo.png'; 

function Login() {
  // --- Estados do Formulário ---
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  
  // --- Estados de UI (Feedback) ---
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false); // Estado de "carregando"

  // --- Hooks ---
  // Pega a função 'login' do "cérebro" global
  const { login } = useAuth(); 
  // Pega a função 'navigate' do roteador
  const navigate = useNavigate(); 

  /**
   * Lida com o envio (submit) do formulário de login.
   */
  const handleSubmit = async (event) => {
    event.preventDefault(); // Impede o recarregamento da página
    setError('');
    setLoading(true); // Ativa o "carregando" (desabilita o botão)

    try {
      // 1. Chama a função 'login' do 'AuthContext'
      // (O 'AuthContext' é quem lida com 'axios', 'setToken',
      //  'localStorage' e a busca do 'GET /usuarios/me')
      const success = await login(username, password);

      if (success) {
        // 2. SUCESSO: Navega para o Dashboard
        // (O 'App.jsx' vai detectar o novo 'token' e
        //  renderizar o 'MainLayout')
        navigate('/'); 
      } else {
        // 3. FALHA (Ex: 401 Unauthorized)
        setError('Nome de usuário ou senha incorretos.');
        setLoading(false); // Para o "carregando" se der erro
      }
    } catch (err) {
      // 4. FALHA (Ex: "ERR_NETWORK" - API "dormindo" ou offline)
      console.error('Erro no handleSubmit do Login:', err);
      setError('Ocorreu um erro inesperado. Tente novamente.');
      setLoading(false);
    }
  };

  return (
    // 'login-page-wrapper' centraliza o card na tela
    <div className="login-page-wrapper">
      <div className="login-container">

        {/* Logo da Marca */}
        <img src={logoNomad} alt="Logo NOMAD" className="login-logo" />

        <h1 className="login-title">NOMAD</h1>
        <p className="login-subtitle">Offline. Sempre. Seu.</p>

        <form className="login-form" onSubmit={handleSubmit}>

          {/* Mostra o erro aqui */}
          {error && <p className="error-message">{error}</p>}

          <div className="input-group">
            {/* (V4.0) Input com estilo "underline" */}
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Nome de usuário" // (Refatorado de 'E-mail')
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
            {/* (Placeholder para a V8.0 de recuperação de senha) */}
            {/* <Link to="/forgot-password" className="login-link">Esqueci minha senha</Link> */}
          </div>
        </form>
      </div>
    </div>
  );
}

export default Login;