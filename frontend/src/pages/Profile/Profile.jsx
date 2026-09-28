// Arquivo: frontend/src/pages/Profile/Profile.jsx
/**
 * @file Página de Perfil e Gerenciamento de Conta.
 * @description Permite visualização e edição de dados do usuário, alteração de senha e logout.
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../../context/useAuth';
import api from '../../services/api';
import './Profile.css';

/**
 * Formata um objeto Date para string no formato 'AAAA-MM-DD'.
 * @param {Date} dateObject - O objeto de data.
 * @returns {string} A string de data formatada.
 */
const formatISODate = (dateObject) => {
  if (!dateObject) return '';
  const date = new Date(dateObject); 
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  return `${year}-${month}-${day}`;
};

/**
 * Manipula a alteração de data no input, corrigindo o fuso horário.
 * @param {Event} event - O evento de input.
 * @param {function} setDate - A função setter para o estado da data.
 */
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

/**
 * Componente de Perfil.
 *
 * Exibe formulários para atualização de dados cadastrais e troca de senha.
 * Gerencia o logout do usuário.
 *
 * @returns {JSX.Element} A página de perfil renderizada.
 */
function Profile() {
  const { user, logout } = useAuth(); 

  // --- Estados do Formulário de Perfil ---
  const [nomeUsuario, setNomeUsuario] = useState('');
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

  /**
   * Efeito colateral que preenche o formulário com dados do usuário logado.
   */
  useEffect(() => {
    if (user) {
      setNomeUsuario(user.nome_usuario || '');
      setNomeCompleto(user.nome_completo || '');
      setEmail(user.email || '');
      setAvatarUrl(user.avatar_url || '');
      
      if (user.data_nascimento) {
        handleDateChange({ target: { value: user.data_nascimento } }, setDataNascimento);
      } else {
        setDataNascimento(null);
      }
    }
  }, [user]);

  /**
   * Manipula a atualização dos dados do perfil.
   * Se o nome de usuário for alterado, força o logout.
   *
   * @param {Event} event - O evento de submit.
   */
  const handleProfileSubmit = async (event) => {
    event.preventDefault();
    setProfileLoading(true);
    setProfileError('');
    setProfileSuccess('');
    
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
      
      if (usernameChanged) {
        setProfileSuccess('Nome de usuário alterado! Por favor, faça o login novamente.');
        setTimeout(() => {
          logout();
        }, 2000);
      }

    } catch (err) {
      console.error("Erro ao atualizar perfil:", err);
      if (err.response && err.response.status === 400) {
        setProfileError(err.response.data.detail);
      } else {
        setProfileError("Não foi possível atualizar o perfil.");
      }
      setProfileLoading(false);
    }
  };

  /**
   * Manipula a alteração de senha.
   * Realiza validações básicas e chama a API.
   *
   * @param {Event} event - O evento de submit.
   */
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

  /**
   * Realiza o logout do usuário.
   */
  const handleLogout = () => {
    logout();
  };

  /** Iniciais exibidas quando não há foto de avatar. */
  const iniciais = (user?.nome_completo || user?.nome_usuario || '?')
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((parte) => parte[0]?.toUpperCase())
    .join('');

  return (
    <>
      <header className="cabecalho-pagina">
        <div>
          <h1>Perfil</h1>
          <p>Seus dados de acesso e informações pessoais.</p>
        </div>
        <div className="acoes-pagina">
          <button type="button" className="botao botao-secundario" onClick={handleLogout}>
            Sair
          </button>
        </div>
      </header>

      <div className="perfil">
        <div className="perfil-identidade">
          {avatarUrl ? (
            <img src={avatarUrl} alt="" className="perfil-avatar" />
          ) : (
            <div className="perfil-avatar" aria-hidden="true">
              {iniciais}
            </div>
          )}
          <div>
            <div className="perfil-nome">
              {user?.nome_completo || user?.nome_usuario || 'Usuário'}
            </div>
            <div className="perfil-usuario">@{user?.nome_usuario}</div>
          </div>
        </div>

        {/* --- Dados pessoais --- */}
        <section className="config-secao">
          <header>
            <h2>Informações pessoais</h2>
            <p>Nome, e-mail e data de nascimento ficam cifrados no servidor.</p>
          </header>

          <form className="config-corpo" onSubmit={handleProfileSubmit}>
            {profileSuccess && (
              <p className="mensagem mensagem-sucesso">{profileSuccess}</p>
            )}
            {profileError && <p className="mensagem mensagem-erro">{profileError}</p>}

            <div className="perfil-form">
              <div>
                <label className="rotulo" htmlFor="nome_usuario">
                  Usuário
                </label>
                <input
                  id="nome_usuario"
                  className="campo"
                  value={nomeUsuario}
                  onChange={(e) => setNomeUsuario(e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="rotulo" htmlFor="nome_completo">
                  Nome completo
                </label>
                <input
                  id="nome_completo"
                  className="campo"
                  value={nomeCompleto}
                  onChange={(e) => setNomeCompleto(e.target.value)}
                />
              </div>

              <div>
                <label className="rotulo" htmlFor="email">
                  E-mail
                </label>
                <input
                  id="email"
                  type="email"
                  className="campo"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div>
                <label className="rotulo" htmlFor="data_nascimento">
                  Data de nascimento
                </label>
                <input
                  id="data_nascimento"
                  type="date"
                  className="campo"
                  value={dataNascimento ? formatISODate(dataNascimento) : ''}
                  onChange={(e) => handleDateChange(e, setDataNascimento)}
                  max={formatISODate(new Date())}
                />
              </div>

              <div className="largura-total">
                <label className="rotulo" htmlFor="avatar_url">
                  URL da foto
                </label>
                <input
                  id="avatar_url"
                  type="url"
                  className="campo"
                  placeholder="https://…"
                  value={avatarUrl}
                  onChange={(e) => setAvatarUrl(e.target.value)}
                />
              </div>
            </div>

            <button
              type="submit"
              className="botao botao-primario"
              style={{ alignSelf: 'flex-start' }}
              disabled={profileLoading}
            >
              {profileLoading ? 'Salvando…' : 'Salvar'}
            </button>
          </form>
        </section>

        {/* --- Senha --- */}
        <section className="config-secao">
          <header>
            <h2>Alterar senha</h2>
            <p>Trocar a senha encerra todas as sessões abertas.</p>
          </header>

          <form className="config-corpo" onSubmit={handlePasswordSubmit}>
            {passwordSuccess && (
              <p className="mensagem mensagem-sucesso">{passwordSuccess}</p>
            )}
            {passwordError && <p className="mensagem mensagem-erro">{passwordError}</p>}

            <div className="perfil-form">
              <div>
                <label className="rotulo" htmlFor="senha_antiga">
                  Senha atual
                </label>
                <input
                  id="senha_antiga"
                  type="password"
                  className="campo"
                  value={senhaAntiga}
                  onChange={(e) => setSenhaAntiga(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>

              <div>
                <label className="rotulo" htmlFor="senha_nova">
                  Nova senha
                </label>
                <input
                  id="senha_nova"
                  type="password"
                  className="campo"
                  value={senhaNova}
                  onChange={(e) => setSenhaNova(e.target.value)}
                  autoComplete="new-password"
                  minLength={12}
                  required
                />
              </div>

              <div>
                <label className="rotulo" htmlFor="senha_confirmar">
                  Confirmar nova senha
                </label>
                <input
                  id="senha_confirmar"
                  type="password"
                  className="campo"
                  value={senhaConfirmar}
                  onChange={(e) => setSenhaConfirmar(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="botao botao-primario"
              style={{ alignSelf: 'flex-start' }}
              disabled={passwordLoading}
            >
              {passwordLoading ? 'Alterando…' : 'Alterar senha'}
            </button>
          </form>
        </section>
      </div>
    </>
  );
}

export default Profile;
