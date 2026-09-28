// Arquivo: frontend/src/pages/SignUp/SignUp.jsx
/**
 * @file Tela de Cadastro.
 * @description Criação de conta, com a política de senha visível desde o início.
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import logo from '../../assets/logo.png';
import { useAuth } from '../../context/useAuth';
import api from '../../services/api';
import '../../styles/auth.css';

/** Mínimo exigido pelo backend (`security.TAMANHO_MINIMO_SENHA`). */
const TAMANHO_MINIMO_SENHA = 12;

/**
 * Tela de cadastro.
 *
 * A política de senha é informada antes do envio, e não apenas como erro
 * depois: o usuário não deveria descobrir a regra sendo recusado por ela.
 *
 * @returns {JSX.Element} A tela de cadastro.
 */
function SignUp() {
  const navegar = useNavigate();
  const { login } = useAuth();

  const [usuario, setUsuario] = useState('');
  const [senha, setSenha] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [erro, setErro] = useState('');
  const [enviando, setEnviando] = useState(false);

  /**
   * Cria a conta e já autentica o usuário.
   *
   * @param {React.FormEvent} evento - O evento de submit.
   */
  const enviar = async (evento) => {
    evento.preventDefault();
    setErro('');

    if (senha !== confirmacao) {
      setErro('As senhas não coincidem.');
      return;
    }

    if (senha.length < TAMANHO_MINIMO_SENHA) {
      setErro(`A senha precisa ter ao menos ${TAMANHO_MINIMO_SENHA} caracteres.`);
      return;
    }

    setEnviando(true);

    try {
      await api.post('/usuarios/', { nome_usuario: usuario, senha });

      const resultado = await login(usuario, senha);
      if (resultado.ok && !resultado.mfaRequerido) {
        navegar('/', { replace: true });
      }
    } catch (err) {
      const detalhe = err.response?.data?.detail;

      // O backend devolve a lista de problemas da política de senha; exibi-la
      // é mais útil do que uma mensagem genérica.
      if (detalhe?.problemas?.length) {
        setErro(detalhe.problemas.join(' '));
      } else if (typeof detalhe === 'string') {
        setErro(detalhe);
      } else {
        setErro('Não foi possível criar a conta. Tente novamente.');
      }
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="auth-tela">
      <div className="auth-card">
        <div className="auth-marca">
          <img src={logo} alt="" />
          NOMAD
        </div>

        <h1>Criar conta</h1>
        <p>Comece a organizar suas finanças em poucos segundos.</p>

        <form className="auth-form" onSubmit={enviar}>
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
              minLength={3}
              maxLength={100}
              pattern="[a-zA-Z0-9._\-]+"
              title="Apenas letras, números, ponto, hífen e sublinhado."
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
              autoComplete="new-password"
              minLength={TAMANHO_MINIMO_SENHA}
              required
            />
            <p className="texto-secundario" style={{ fontSize: 'var(--t-xs)', marginTop: 'var(--e-2)' }}>
              Mínimo de {TAMANHO_MINIMO_SENHA} caracteres.
            </p>
          </div>

          <div>
            <label className="rotulo" htmlFor="confirmacao">
              Confirmar senha
            </label>
            <input
              id="confirmacao"
              type="password"
              className="campo"
              value={confirmacao}
              onChange={(e) => setConfirmacao(e.target.value)}
              autoComplete="new-password"
              required
            />
          </div>

          <button type="submit" className="botao botao-primario" disabled={enviando}>
            {enviando ? 'Criando…' : 'Criar conta'}
          </button>
        </form>

        <p className="auth-rodape">
          Já tem conta? <Link to="/login">Entrar</Link>
        </p>
      </div>
    </div>
  );
}

export default SignUp;
