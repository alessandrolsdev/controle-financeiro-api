// Arquivo: frontend/src/pages/Login/Login.jsx
/**
 * @file Tela de Login.
 * @description Autenticação em uma ou duas etapas, conforme o segundo fator.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';

import logo from '../../assets/logo.png';
import { useAuth } from '../../context/useAuth';
import '../../styles/auth.css';

/**
 * Tela de login.
 *
 * Quando a conta tem segundo fator, a senha correta não abre sessão: o
 * formulário troca para a etapa do código, usando o token de desafio recebido.
 *
 * @returns {JSX.Element} A tela de login.
 */
function Login() {
  const { login, verificarSegundoFator } = useAuth();

  const [usuario, setUsuario] = useState('');
  const [senha, setSenha] = useState('');
  const [codigo, setCodigo] = useState('');
  const [desafio, setDesafio] = useState(null);
  const [erro, setErro] = useState('');
  const [enviando, setEnviando] = useState(false);

  /**
   * Envia as credenciais da primeira etapa.
   *
   * @param {React.FormEvent} evento - O evento de submit.
   */
  const enviarCredenciais = async (evento) => {
    evento.preventDefault();
    setErro('');
    setEnviando(true);

    const resultado = await login(usuario, senha);
    setEnviando(false);

    if (!resultado.ok) {
      setErro(resultado.erro);
      return;
    }

    if (resultado.mfaRequerido) {
      setDesafio(resultado.desafio);
    }
    // Sem MFA, o contexto já carregou o perfil e o roteador redireciona.
  };

  /**
   * Envia o código do segundo fator.
   *
   * @param {React.FormEvent} evento - O evento de submit.
   */
  const enviarCodigo = async (evento) => {
    evento.preventDefault();
    setErro('');
    setEnviando(true);

    const resultado = await verificarSegundoFator(desafio, codigo);
    setEnviando(false);

    if (!resultado.ok) {
      setErro(resultado.erro);
      setCodigo('');
    }
  };

  return (
    <div className="auth-tela">
      <div className="auth-card">
        <div className="auth-marca">
          <img src={logo} alt="" />
          NOMAD
        </div>

        {desafio ? (
          <>
            <h1>Verificação em duas etapas</h1>
            <p>
              Digite o código do seu aplicativo autenticador ou um código de
              recuperação.
            </p>

            <form className="auth-form" onSubmit={enviarCodigo}>
              {erro && <p className="mensagem mensagem-erro">{erro}</p>}

              <div>
                <label className="rotulo" htmlFor="codigo">
                  Código
                </label>
                <input
                  id="codigo"
                  className="campo auth-codigo"
                  value={codigo}
                  onChange={(e) => setCodigo(e.target.value)}
                  autoComplete="one-time-code"
                  inputMode="text"
                  maxLength={32}
                  required
                  autoFocus
                />
              </div>

              <button
                type="submit"
                className="botao botao-primario"
                disabled={enviando}
              >
                {enviando ? 'Verificando…' : 'Verificar'}
              </button>
            </form>

            <p className="auth-alternativa">
              <button
                type="button"
                className="botao-discreto"
                onClick={() => {
                  setDesafio(null);
                  setCodigo('');
                  setErro('');
                }}
              >
                Usar outra conta
              </button>
            </p>
          </>
        ) : (
          <>
            <h1>Entrar</h1>
            <p>Acesse sua conta para ver seu painel financeiro.</p>

            <form className="auth-form" onSubmit={enviarCredenciais}>
              {erro && <p className="mensagem mensagem-erro">{erro}</p>}

              <div>
                <label className="rotulo" htmlFor="usuario">
                  Usuário
                </label>
                <input
                  id="usuario"
                  className="campo"
                  value={usuario}
                  onChange={(e) => setUsuario(e.target.value)}
                  autoComplete="username"
                  required
                  autoFocus
                />
              </div>

              <div>
                <label className="rotulo" htmlFor="senha">
                  Senha
                </label>
                <input
                  id="senha"
                  type="password"
                  className="campo"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>

              <button
                type="submit"
                className="botao botao-primario"
                disabled={enviando}
              >
                {enviando ? 'Entrando…' : 'Entrar'}
              </button>
            </form>

            <p className="auth-rodape">
              Não tem conta? <Link to="/signup">Criar conta</Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default Login;
