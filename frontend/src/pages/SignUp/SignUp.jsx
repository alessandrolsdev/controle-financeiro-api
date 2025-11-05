// Arquivo: frontend/src/pages/SignUp/SignUp.jsx
// Responsabilidade: "Página" (cômodo) de Cadastro de Novo Usuário.
// É uma rota pública para que novos usuários possam se registrar.

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios'; // Usamos axios direto, pois o 'api.js' só funciona logado
import './SignUp.css'; // Usaremos um CSS próprio (copiado do Login)
import logoNomad from '../../assets/logo.png'; // Nosso logo

/**
 * Componente da página de Cadastro (Sign Up).
 * Permite que um novo usuário crie uma conta.
 */
function SignUp() {
  // --- Estados do Formulário ---
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  
  // --- Estados de Feedback (UI) ---
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(''); // Para a mensagem de sucesso
  
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
      // Usamos a variável de ambiente VITE_API_BASE_URL
      await axios.post(`${import.meta.env.VITE_API_BASE_URL}/usuarios/`, {
        nome_usuario: username,
        senha: password,
      });

      // 2. SUCESSO!
      setLoading(false);
      setSuccess('Conta criada com sucesso! Redirecionando para o login...');

      // 3. Espera 2 segundos e redireciona o usuário para o Login
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

// --- A LINHA QUE FALTAVA ---
export default SignUp;