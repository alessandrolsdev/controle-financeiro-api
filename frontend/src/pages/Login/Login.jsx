// Arquivo: frontend/src/pages/Login/Login.jsx
// (VERSÃO V2.0 - DESIGN "AZUL GUARDIÃO" / "NOMAD")

import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import './Login.css'; // Importa os nossos novos estilos

// 1. IMPORTA O LOGO
// O React/Vite encontrará o logo na pasta 'assets'
import logoNomad from '../../assets/logo.png'; // Certifique-se que o nome do arquivo é 'logo.png'

/**
 * Componente da Página de Login, agora com o design "NOMAD".
 */
function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false); // Estado de "carregando"

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true); // Ativa o "carregando"

    try {
      const success = await login(username, password);

      if (success) {
        navigate('/'); // Redireciona para o Dashboard
      } else {
        setError('Nome de usuário ou senha incorretos.');
        setLoading(false); // Para o "carregando" se der erro
      }
    } catch (err) {
      console.error('Erro no handleSubmit do Login:', err);
      setError('Ocorreu um erro inesperado. Tente novamente.');
      setLoading(false);
    }
  };

  // --- O NOVO JSX (baseado no seu mockup) ---
  return (
    // O 'login-page-wrapper' ajuda a centralizar verticalmente
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
            {/* Usamos o placeholder como label, como no mockup */}
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="E-mail"
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

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Entrando...' : 'ENTRAR'}
          </button>

          <div className="login-links">
            <Link to="/forgot-password" className="login-link">Esqueci minha senha</Link>
            <Link to="/signup" className="login-link">Criar nova conta</Link>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Login;