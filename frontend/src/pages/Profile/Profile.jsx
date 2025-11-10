// Arquivo: frontend/src/pages/Profile/Profile.jsx
/*
 * Página de Perfil e Gerenciamento de Conta (V7.2).
 *
 * Esta página é um "Filho" do 'MainLayout'.
 * Ela permite ao usuário visualizar e editar suas informações
 * pessoais, alterar seu nome de usuário (login) e
 * alterar sua senha.
 *
 * Decisão de Arquitetura (V7.1):
 * Esta página NÃO busca (fetch) seus próprios dados.
 * Ela lê o objeto 'user' completo diretamente do 'useAuth()',
 * que é preenchido quando o 'AuthContext' chama 'GET /usuarios/me'.
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext'; // O "cérebro" (para 'user' e 'logout')
import api from '../../services/api'; // O "embaixador"
import './Profile.css'; // Estilos locais

// --- Funções Auxiliares (Helpers) de Data ---
// (Necessárias para formatar a data entre o objeto Date()
//  e o input <input type="date">)

/**
 * Formata um objeto Date() para a string "AAAA-MM-DD"
 * que o '<input type="date">' exige como valor.
 */
const formatISODate = (dateObject) => {
  if (!dateObject) return '';
  // Garante que 'dateObject' seja um objeto Date válido
  const date = new Date(dateObject); 
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  return `${year}-${month}-${day}`;
};

/**
 * Lida com a mudança do calendário.
 * Converte a string 'AAAA-MM-DD' (do input) para um
 * objeto Date() no fuso horário local correto.
 */
const handleDateChange = (event, setDate) => {
  const dateString = event.target.value;
  if (!dateString) {
    setDate(null);
    return;
  }
  const data = new Date(dateString);
  // (V2.9) Trata o fuso horário para não pular um dia
  const dataLocal = new Date(data.valueOf() + data.getTimezoneOffset() * 60000);
  setDate(dataLocal);
};
// ---------------------------------------------------


function Profile() {
  // 1. Pega o 'user' (objeto de perfil completo) e 'logout' do "cérebro"
  const { user, logout } = useAuth(); 

  // --- Estados do Formulário de Perfil ---
  const [nomeUsuario, setNomeUsuario] = useState('');
  const [nomeCompleto, setNomeCompleto] = useState('');
  const [email, setEmail] = useState('');
  const [dataNascimento, setDataNascimento] = useState(null); // (Objeto Date())
  const [avatarUrl, setAvatarUrl] = useState('');
  
  // --- Estados do Formulário de Senha ---
  const [senhaAntiga, setSenhaAntiga] = useState('');
  const [senhaNova, setSenhaNova] = useState('');
  const [senhaConfirmar, setSenhaConfirmar] = useState('');

  // --- Estados de UI (Feedback e Loading) ---
  const [profileLoading, setProfileLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  
  const [profileSuccess, setProfileSuccess] = useState('');
  const [profileError, setProfileError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [passwordError, setPasswordError] = useState('');


  /**
   * Efeito [user]: Sincroniza o 'user' (do Context) com o estado local.
   *
   * Quando o 'AuthContext' termina de carregar o 'user',
   * este efeito preenche os campos do formulário.
   */
  useEffect(() => {
    if (user) {
      setNomeUsuario(user.nome_usuario || '');
      setNomeCompleto(user.nome_completo || '');
      setEmail(user.email || '');
      setAvatarUrl(user.avatar_url || '');
      
      // (Usa o helper para garantir que a data (que vem como AAAA-MM-DD
      //  do JSON) seja convertida corretamente para o fuso local)
      if (user.data_nascimento) {
        handleDateChange({ target: { value: user.data_nascimento } }, setDataNascimento);
      } else {
        setDataNascimento(null);
      }
    }
  }, [user]); // <-- O gatilho é o 'user' do AuthContext


  /**
   * HANDLER 1: Salvar Detalhes do Perfil (V7.2).
   * Chama 'PUT /usuarios/me'.
   */
  const handleProfileSubmit = async (event) => {
    event.preventDefault();
    setProfileLoading(true);
    setProfileError('');
    setProfileSuccess('');
    
    // Verifica se o nome de usuário (login) foi alterado
    const usernameChanged = (user && user.nome_usuario !== nomeUsuario);
    
    try {
      await api.put('/usuarios/me', {
        nome_usuario: nomeUsuario,
        nome_completo: nomeCompleto,
        email: email,
        data_nascimento: dataNascimento ? formatISODate(dataNascimento) : null,
        avatar_url: avatarUrl
      });
      setProfileLoading(false);
      setProfileSuccess('Perfil atualizado com sucesso!');
      
      // Decisão de Segurança (V7.2):
      // Se o usuário mudou o 'nome_usuario' (seu login), o token JWT
      // antigo (baseado no 'sub' antigo) torna-se inválido.
      // Devemos forçar o logout para que ele se autentique novamente.
      if (usernameChanged) {
        setProfileSuccess('Nome de usuário alterado! Por favor, faça o login novamente.');
        setTimeout(() => {
          logout();
        }, 2000); // (Espera 2s para o usuário ler a msg)
      }

    } catch (err) {
      console.error("Erro ao atualizar perfil:", err);
      if (err.response && err.response.status === 400) {
        // (Pega o erro do backend, ex: "Esse nome de usuário já está em uso.")
        setProfileError(err.response.data.detail);
      } else {
        setProfileError("Não foi possível atualizar o perfil.");
      }
      setProfileLoading(false);
    }
  };

  /**
   * HANDLER 2: Mudar Senha (V7.0).
   * Chama 'POST /usuarios/mudar-senha'.
   */
  const handlePasswordSubmit = async (event) => {
    event.preventDefault();
    setPasswordLoading(true);
    setPasswordError('');
    setPasswordSuccess('');

    // Validação de frontend
    if (senhaNova !== senhaConfirmar) {
      setPasswordError("As novas senhas não conferem.");
      setPasswordLoading(false);
      return;
    }
    if (senhaNova.length < 4) { // (Regra de negócio simples)
       setPasswordError("A nova senha deve ter pelo menos 4 caracteres.");
       setPasswordLoading(false);
       return;
    }

    try {
      // Chama o endpoint de mudança de senha
      await api.post('/usuarios/mudar-senha', {
        senha_antiga: senhaAntiga,
        senha_nova: senhaNova
      });
      
      setPasswordLoading(false);
      setPasswordSuccess('Senha alterada com sucesso!');
      
      // Limpa os campos de senha por segurança
      setSenhaAntiga('');
      setSenhaNova('');
      setSenhaConfirmar('');
    } catch (err) {
      console.error("Erro ao mudar senha:", err);
      if (err.response && err.response.status === 400) {
        // (Pega o erro do backend, ex: "A senha antiga está incorreta.")
        setPasswordError(err.response.data.detail);
      } else {
        setPasswordError("Não foi possível alterar a senha.");
      }
      setPasswordLoading(false);
    }
  };

  /**
   * HANDLER 3: Logout.
   * Chama a função 'logout()' do AuthContext.
   */
  const handleLogout = () => {
    logout();
  };

  return (
    <div className="profile-container">
      <header className="profile-header">
        <h2>Perfil e Ajustes</h2>
      </header>

      <main className="profile-content">
        
        {/* Card 1: Avatar e Nome */}
        <div className="profile-card avatar-card">
          {avatarUrl ? (
            <img src={avatarUrl} alt="Avatar" className="avatar-image" />
          ) : (
            <div className="avatar-placeholder">
              <span>(Sem foto)</span>
            </div>
          )}
          {/* (V7.2) Usa o "Nome Completo" (se existir) ou o "Nome de Usuário" */}
          <h3>Olá, {user ? (user.nome_completo || user.nome_usuario) : 'Usuário'}!</h3>
        </div>

        {/* Card 2: Informações Pessoais e Login (V7.2) */}
        <form className="profile-card" onSubmit={handleProfileSubmit}>
          <h2>Informações Pessoais e Login</h2>
          
          {profileSuccess && <p className="success-message">{profileSuccess}</p>}
          {profileError && <p className="error-message">{profileError}</p>}
          
          <>
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
                max={formatISODate(new Date())} // (V2.10) Impede datas futuras
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

        {/* Card 3: Mudar Senha (V7.0) */}
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