// Arquivo: frontend/src/pages/Login/Login.jsx

import React from 'react';
import './Login.css'; // Importa nosso CSS

function Login() {
  return (
    <div className="login-container">
      <form className="login-form">
        <h2>Login</h2>
        <div className="input-group">
          <label htmlFor="username">Usuário</label>
          <input
            type="text"
            id="username"
            placeholder="Digite seu usuário"
          />
        </div>
        <div className="input-group">
          <label htmlFor="password">Senha</label>
          <input
            type="password"
            id="password"
            placeholder="Digite sua senha"
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