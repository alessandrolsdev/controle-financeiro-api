// Arquivo: frontend/src/pages/Profile/Profile.jsx
// (VERSÃO V7.2 - COMPLETA COM "MUDAR NOME DE USUÁRIO")
/*
REATORAÇÃO (Missão V7.2):
1. Adiciona o estado 'nomeUsuario' (para o login).
2. O 'useEffect' agora preenche o 'nomeUsuario'.
3. O 'handleProfileSubmit' agora envia o 'nomeUsuario'
   e verifica se ele foi alterado.
4. Se o 'nome_usuario' foi alterado, chama 'logout()'
   para forçar um novo login (o token antigo é invalidado).
*/

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';
import './Profile.css';

// --- Funções Auxiliares (Trazidas do Dashboard) ---
const formatISODate = (dateObject) => {
  if (!dateObject) return '';
  const date = new Date(dateObject); 
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  return `${year}-${month}-${day}`;
};
const handleDateChange = (event, setDate) => {
  const dateString = event.target.value;
  if (!dateString) {
    setDate(null);
    return;
  }
  const data = new Date(dateString);
  const dataLocal = new Date(data.valueOf() + data.getTimezoneOffset() * 60000);
  setDate(dataLocal);
};
// ---------------------------------------------------

function Profile() {
  const { user, logout } = useAuth(); 

  // --- Estados do Formulário de Perfil ---
  const [nomeUsuario, setNomeUsuario] = useState(''); // <-- NOVO (V7.2)
  const [nomeCompleto, setNomeCompleto] = useState('');
  const [email, setEmail] = useState('');
  const [dataNascimento, setDataNascimento] = useState(null);
  const [avatarUrl, setAvatarUrl] = useState('');
  
  // --- Estados do Formulário de Senha ---
  const [senhaAntiga, setSenhaAntiga] = useState('');
  const [senhaNova, setSenhaNova] = useState('');
  const [senhaConfirmar, setSenhaConfirmar] = useState('');

  // --- Estados de UI ---
  const [profileLoading, setProfileLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState('');
  const [profileError, setProfileError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [passwordError, setPasswordError] = useState('');

  // --- EFEITO DE "PREENCHIMENTO" ---
  useEffect(() => {
    if (user) {
      setNomeUsuario(user.nome_usuario || ''); // <-- NOVO (V7.2)
      setNomeCompleto(user.nome_completo || '');
      setEmail(user.email || '');
      setAvatarUrl(user.avatar_url || '');
      if (user.data_nascimento) {
        handleDateChange({ target: { value: user.data_nascimento } }, setDataNascimento);
      } else {
        setDataNascimento(null);
      }
    }
  }, [user]); // Ouve o 'user' do AuthContext


  // --- HANDLER 1: Salvar Detalhes do Perfil (ATUALIZADO V7.2) ---
  const handleProfileSubmit = async (event) => {
    event.preventDefault();
    setProfileLoading(true);
    setProfileError('');
    setProfileSuccess('');
    
    // Verifica se o nome de usuário (login) foi alterado
    const usernameChanged = (user && user.nome_usuario !== nomeUsuario);
    
    try {
      await api.put('/usuarios/me', {
        nome_usuario: nomeUsuario, // <-- ENVIA O NOME DE USUÁRIO
        nome_completo: nomeCompleto,
        email: email,
        data_nascimento: dataNascimento ? formatISODate(dataNascimento) : null,
        avatar_url: avatarUrl
      });
      setProfileLoading(false);
      setProfileSuccess('Perfil atualizado com sucesso!');
      
      // ARQUITETURA DE SEGURANÇA (V7.2)
      // Se o usuário mudou o login, o token JWT antigo (baseado
      // no 'sub' antigo) torna-se inválido. Devemos forçar o logout.
      if (usernameChanged) {
        setProfileSuccess('Nome de usuário alterado! Por favor, faça o login novamente.');
        setTimeout(() => {
          logout();
        }, 2000); // Espera 2s para o usuário ler a msg
      }

    } catch (err) {
      console.error("Erro ao atualizar perfil:", err);
      if (err.response && err.response.status === 400) {
        setProfileError(err.response.data.detail); // Ex: "Esse nome de usuário já está em uso."
      } else {
        setProfileError("Não foi possível atualizar o perfil.");
      }
      setProfileLoading(false);
    }
  };

  // --- HANDLER 2: Mudar Senha (Sem mudança) ---
  const handlePasswordSubmit = async (event) => {
    event.preventDefault();
    setPasswordLoading(true);
    setPasswordError('');
    setPasswordSuccess('');
    if (senhaNova !== senhaConfirmar) {
      setPasswordError("As novas senhas não conferem.");
      setPasswordLoading(false);
      return;
    }
    if (senhaNova.length < 4) {
       setPasswordError("A nova senha deve ter pelo menos 4 caracteres.");
       setPasswordLoading(false);
       return;
    }
    try {
      await api.post('/usuarios/mudar-senha', {
        senha_antiga: senhaAntiga,
        senha_nova: senhaNova
      });
      setPasswordLoading(false);
      setPasswordSuccess('Senha alterada com sucesso!');
      setSenhaAntiga('');
      setSenhaNova('');
      setSenhaConfirmar('');
    } catch (err) {
      console.error("Erro ao mudar senha:", err);
      if (err.response && err.response.status === 400) {
        setPasswordError(err.response.data.detail);
      } else {
        setPasswordError("Não foi possível alterar a senha.");
      }
      setPasswordLoading(false);
    }
  };

  // --- HANDLER 3: Logout (Sem mudança) ---
  const handleLogout = () => {
    logout();
  };

  return (
    <div className="profile-container">
      <header className="profile-header">
        <h2>Perfil e Ajustes</h2>
      </header>

      <main className="profile-content">
        
        <div className="profile-card avatar-card">
          {avatarUrl ? (
            <img src={avatarUrl} alt="Avatar" className="avatar-image" />
          ) : (
            <div className="avatar-placeholder">
              <span>(Sem foto)</span>
            </div>
          )}
          {/* (Correção V7.2) */}
          <h3>Olá, {user ? (user.nome_completo || user.nome_usuario) : 'Usuário'}!</h3>
        </div>

        {/* Card 2: Informações Pessoais (ATUALIZADO V7.2) */}
        <form className="profile-card" onSubmit={handleProfileSubmit}>
          <h2>Informações Pessoais e Login</h2>
          
          {profileSuccess && <p className="success-message">{profileSuccess}</p>}
          {profileError && <p className="error-message">{profileError}</p>}
          
          <>
            {/* O NOVO CAMPO DE NOME DE USUÁRIO */}
            <div className="input-group">
              <label htmlFor="nome_usuario">Nome de Usuário (Login)</label>
              <input
                type="text"
                id="nome_usuario"
                placeholder="Seu nome de login"
                value={nomeUsuario}
                onChange={(e) => setNomeUsuario(e.target.value)}
                required
              />
            </div>
          
            <div className="input-group">
              <label htmlFor="nome_completo">Nome Completo (Para o "Olá, [Nome]")</label>
              <input
                type="text"
                id="nome_completo"
                placeholder="Seu Nome Completo"
                value={nomeCompleto}
                onChange={(e) => setNomeCompleto(e.target.value)}
              />
            </div>

            <div className="input-group">
              <label htmlFor="email">E-mail (Para futura recuperação)</label>
              <input
                type="email"
                id="email"
                placeholder="seu.email@exemplo.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            
            <div className="input-group">
              <label htmlFor="data_nascimento">Data de Nascimento</label>
              <input
                type="date"
                id="data_nascimento"
                value={dataNascimento ? formatISODate(dataNascimento) : ''}
                onChange={(e) => handleDateChange(e, setDataNascimento)}
                max={formatISODate(new Date())}
              />
            </div>
            
            <div className="input-group">
              <label htmlFor="avatar_url">URL da Foto (Avatar)</label>
              <input
                type="url"
                id="avatar_url"
                placeholder="https://i.imgur.com/seu-link.jpg"
                value={avatarUrl}
                onChange={(e) => setAvatarUrl(e.target.value)}
              />
            </div>
            
            <button type="submit" className="profile-button-save" disabled={profileLoading}>
              {profileLoading ? 'Salvando...' : 'Salvar Alterações do Perfil'}
            </button>
          </>
        </form>

        {/* Card 3: Mudar Senha */}
        <form className="profile-card" onSubmit={handlePasswordSubmit}>
          <h2>Alterar Senha</h2>

          {passwordSuccess && <p className="success-message">{passwordSuccess}</p>}
          {passwordError && <p className="error-message">{passwordError}</p>}
          
          <div className="input-group">
            <label htmlFor="senha_antiga">Senha Antiga</label>
            <input
              type="password"
              id="senha_antiga"
              placeholder="Sua senha atual"
              value={senhaAntiga}
              onChange={(e) => setSenhaAntiga(e.target.value)}
              required
            />
          </div>
          <div className="input-group">
            <label htmlFor="senha_nova">Nova Senha</label>
            <input
              type="password"
              id="senha_nova"
              placeholder="Mínimo 4 caracteres"
              value={senhaNova}
              onChange={(e) => setSenhaNova(e.target.value)}
              required
            />
          </div>
          <div className="input-group">
            <label htmlFor="senha_confirmar">Confirmar Nova Senha</label>
            <input
              type="password"
              id="senha_confirmar"
              placeholder="Repita a nova senha"
              value={senhaConfirmar}
              onChange={(e) => setSenhaConfirmar(e.target.value)}
              required
            />
          </div>
          
          <button type="submit" className="profile-button-save" disabled={passwordLoading}>
            {passwordLoading ? 'Alterando...' : 'Alterar Senha'}
          </button>
        </form>

        {/* Card 4: Logout */}
        <div className="profile-card">
          <h2>Sessão</h2>
          <button onClick={handleLogout} className="logout-button-profile">
            Sair da Conta (Logout)
          </button>
        </div>

      </main>
    </div>
  );
}

export default Profile;