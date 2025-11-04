// Arquivo: frontend/src/pages/Login/Login.jsx
// Responsabilidade: "Página" (cômodo) de Login.
// Renderiza o formulário de login e gerencia o estado (usuário, senha, erro).

import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext'; // O "cérebro" do login
import { useNavigate } from 'react-router-dom'; // O "mapa" para redirecionar
import './Login.css'; // Estilos específicos desta página

/**
 * Componente da página de Login.
 * É um formulário "controlado" (controlled component), onde o React
 * gerencia o valor de cada campo de input através de 'useState'.
 */
function Login() { 
  
  // --- 1. Hooks (O "cérebro" do componente) ---
  
  // Estados para controlar os campos do formulário
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  
  // Estado para exibir mensagens de erro ao usuário
  const [error, setError] = useState('');
  
  // Pega a função de 'login' do nosso cérebro global (AuthContext)
  const { login } = useAuth();
  
  // Pega a função 'navigate' do React Router para podermos redirecionar o usuário
  const navigate = useNavigate();

  // --- 2. Função de Envio ---
  
  /**
   * Função chamada quando o usuário clica no botão "Entrar" (envia o formulário).
   * @param {React.FormEvent} event - O evento do formulário.
   */
  const handleSubmit = async (event) => {
    // Impede o comportamento padrão do HTML, que é recarregar a página
    event.preventDefault();
    // Limpa qualquer erro antigo antes de tentar o login
    setError('');

    try {
      // Chama a função 'login' que está no AuthContext.
      // O AuthContext é que faz a chamada de API (axios) para o backend.
      const success = await login(username, password);

      if (success) {
        // Se o login der certo (retornar true)...
        console.log("LOGIN BEM-SUCEDIDO! Redirecionando...");
        navigate('/'); // Redireciona o usuário para o Dashboard (página principal)
      } else {
        // Se o login falhar (retornar false, ex: 401 do backend)...
        setError('Nome de usuário ou senha incorretos.');
      }
    } catch (err) { // Pega erros inesperados (ex: rede caiu)
      console.error('Erro no handleSubmit do Login:', err);
      setError('Ocorreu um erro inesperado. Tente novamente.');
    }
  };

  // --- 3. Renderização do JSX (O que aparece na tela) ---
  return (
    <div className="login-container">
      {/* Conecta nossa função handleSubmit ao evento onSubmit do formulário */}
      <form className="login-form" onSubmit={handleSubmit}>
        <h2>Login</h2>
        
        {/* Renderização Condicional: 
            Mostra o <p> de erro APENAS SE a variável 'error' tiver algum texto */}
        {error && <p className="error-message">{error}</p>}

        {/* Campo de Usuário (Componente Controlado) */}
        <div className="input-group">
          <label htmlFor="username">Usuário</label>
          <input
            type="text"
            id="username"
            placeholder="Digite seu usuário"
            value={username} // O valor é "amarrado" ao nosso estado 'username'
            onChange={(e) => setUsername(e.target.value)} // A cada tecla, atualiza o estado
            required
          />
        </div>

        {/* Campo de Senha (Componente Controlado) */}
        <div className="input-group">
          <label htmlFor="password">Senha</label>
          <input
            type="password"
            id="password"
            placeholder="Digite sua senha"
            value={password} // O valor é "amarrado" ao nosso estado 'password'
            onChange={(e) => setPassword(e.target.value)} // A cada tecla, atualiza o estado
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