// Arquivo: frontend/src/components/SecuritySection/SecuritySection.jsx
/**
 * @file Seção de Segurança da Conta.
 * @description Gerencia o segundo fator (TOTP) e o encerramento de sessões.
 */

import QRCode from 'qrcode';
import { useCallback, useEffect, useRef, useState } from 'react';

import { useAuth } from '../../context/useAuth';
import api from '../../services/api';

/**
 * Seção de segurança da conta.
 *
 * O fluxo de ativação tem duas etapas de propósito: o segredo é gerado e
 * exibido, mas o segundo fator só passa a valer depois que o usuário digita um
 * código válido. Ativar antes disso trancaria a conta caso o QR Code fosse
 * lido incorretamente.
 *
 * @returns {JSX.Element} A seção renderizada.
 */
function SecuritySection() {
  const { logout } = useAuth();

  const [status, setStatus] = useState({ ativado: false, codigos_restantes: 0 });
  const [provisionamento, setProvisionamento] = useState(null);
  const [codigo, setCodigo] = useState('');
  const [codigosDeRecuperacao, setCodigosDeRecuperacao] = useState(null);
  const [senha, setSenha] = useState('');
  const [desativando, setDesativando] = useState(false);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');

  const canvasRef = useRef(null);

  /**
   * Consulta a situação atual do segundo fator.
   *
   * @returns {Promise<void>} Conclui após atualizar o estado.
   */
  const carregarStatus = useCallback(async () => {
    try {
      const { data } = await api.get('/usuarios/me/mfa');
      setStatus(data);
    } catch {
      setErro('Não foi possível carregar as configurações de segurança.');
    }
  }, []);

  useEffect(() => {
    carregarStatus();
  }, [carregarStatus]);

  // Desenha o QR Code assim que a URI de provisionamento chega.
  useEffect(() => {
    if (!provisionamento || !canvasRef.current) return;

    QRCode.toCanvas(canvasRef.current, provisionamento.uri_de_provisionamento, {
      width: 180,
      margin: 0,
      // Módulos escuros sobre fundo claro: é o contraste que os leitores
      // ópticos esperam, independentemente do tema da aplicação.
      color: { dark: '#000000', light: '#ffffff' },
    }).catch(() => setErro('Não foi possível gerar o QR Code.'));
  }, [provisionamento]);

  /**
   * Inicia a ativação, obtendo o segredo TOTP.
   */
  const iniciar = async () => {
    setErro('');
    try {
      const { data } = await api.post('/usuarios/me/mfa/iniciar');
      setProvisionamento(data);
    } catch (err) {
      setErro(err.response?.data?.detail || 'Não foi possível iniciar a ativação.');
    }
  };

  /**
   * Confirma a ativação com um código do aplicativo.
   *
   * @param {React.FormEvent} evento - O evento de submit.
   */
  const confirmar = async (evento) => {
    evento.preventDefault();
    setErro('');

    try {
      const { data } = await api.post('/usuarios/me/mfa/confirmar', { codigo });
      setCodigosDeRecuperacao(data.codigos);
      setProvisionamento(null);
      setCodigo('');
      await carregarStatus();
    } catch (err) {
      setErro(err.response?.data?.detail || 'Código inválido.');
    }
  };

  /**
   * Desativa o segundo fator, exigindo a senha atual.
   *
   * @param {React.FormEvent} evento - O evento de submit.
   */
  const desativar = async (evento) => {
    evento.preventDefault();
    setErro('');

    try {
      await api.post('/usuarios/me/mfa/desativar', { senha });
      setSenha('');
      setDesativando(false);
      setCodigosDeRecuperacao(null);
      await carregarStatus();
    } catch (err) {
      setErro(err.response?.data?.detail || 'Não foi possível desativar.');
    }
  };

  /**
   * Gera um novo lote de códigos de recuperação.
   */
  const regenerarCodigos = async () => {
    setErro('');
    try {
      const { data } = await api.post('/usuarios/me/mfa/codigos');
      setCodigosDeRecuperacao(data.codigos);
      await carregarStatus();
    } catch (err) {
      setErro(err.response?.data?.detail || 'Não foi possível gerar novos códigos.');
    }
  };

  /**
   * Encerra todas as sessões abertas e leva o usuário de volta ao login.
   */
  const encerrarSessoes = async () => {
    if (!window.confirm('Encerrar todas as sessões? Você precisará entrar de novo.')) {
      return;
    }

    try {
      await api.post('/usuarios/me/revogar-sessoes');
      setAviso('Todas as sessões foram encerradas.');
      await logout();
    } catch {
      setErro('Não foi possível encerrar as sessões.');
    }
  };

  return (
    <section className="config-secao">
      <header>
        <h2>Segurança</h2>
        <p>Proteja o acesso à sua conta.</p>
      </header>

      <div className="config-corpo">
        {erro && <p className="mensagem mensagem-erro">{erro}</p>}
        {aviso && <p className="mensagem mensagem-sucesso">{aviso}</p>}

        {/* --- Situação do segundo fator --- */}
        <div className="mfa-status">
          <span className={status.ativado ? 'mfa-indicador ativo' : 'mfa-indicador'}>
            Verificação em duas etapas{' '}
            {status.ativado ? 'ativa' : 'desativada'}
          </span>

          {!status.ativado && !provisionamento && (
            <button type="button" className="botao botao-primario" onClick={iniciar}>
              Ativar
            </button>
          )}

          {status.ativado && !desativando && (
            <div style={{ display: 'flex', gap: 'var(--e-2)' }}>
              <button
                type="button"
                className="botao botao-secundario"
                onClick={regenerarCodigos}
              >
                Novos códigos
              </button>
              <button
                type="button"
                className="botao botao-perigo"
                onClick={() => setDesativando(true)}
              >
                Desativar
              </button>
            </div>
          )}
        </div>

        {status.ativado && !codigosDeRecuperacao && (
          <p className="texto-secundario" style={{ fontSize: 'var(--t-sm)' }}>
            {status.codigos_restantes} código(s) de recuperação restante(s).
          </p>
        )}

        {/* --- Etapa de provisionamento --- */}
        {provisionamento && (
          <>
            <div className="mfa-qr">
              <canvas ref={canvasRef} />
              <p className="texto-secundario" style={{ fontSize: 'var(--t-sm)' }}>
                Leia o código com seu aplicativo autenticador, ou digite a chave:
              </p>
              <code className="mfa-segredo">{provisionamento.segredo}</code>
            </div>

            <form onSubmit={confirmar} className="form-linha">
              <div>
                <label className="rotulo" htmlFor="codigo-mfa">
                  Código do aplicativo
                </label>
                <input
                  id="codigo-mfa"
                  className="campo"
                  value={codigo}
                  onChange={(e) => setCodigo(e.target.value)}
                  inputMode="numeric"
                  maxLength={6}
                  required
                />
              </div>
              <button type="submit" className="botao botao-primario">
                Confirmar
              </button>
              <button
                type="button"
                className="botao botao-secundario"
                onClick={() => {
                  setProvisionamento(null);
                  setCodigo('');
                }}
              >
                Cancelar
              </button>
            </form>
          </>
        )}

        {/* --- Códigos de recuperação (exibidos uma única vez) --- */}
        {codigosDeRecuperacao && (
          <div>
            <p className="mensagem mensagem-sucesso" style={{ marginBottom: 'var(--e-3)' }}>
              Guarde estes códigos agora. Cada um funciona uma única vez e eles
              não serão exibidos de novo.
            </p>
            <ul className="codigos-recuperacao">
              {codigosDeRecuperacao.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {/* --- Desativação --- */}
        {desativando && (
          <form onSubmit={desativar} className="form-linha">
            <div>
              <label className="rotulo" htmlFor="senha-mfa">
                Confirme sua senha
              </label>
              <input
                id="senha-mfa"
                type="password"
                className="campo"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            <button type="submit" className="botao botao-perigo">
              Desativar
            </button>
            <button
              type="button"
              className="botao botao-secundario"
              onClick={() => {
                setDesativando(false);
                setSenha('');
              }}
            >
              Cancelar
            </button>
          </form>
        )}

        {/* --- Sessões --- */}
        <div className="mfa-status" style={{ borderTop: '1px solid var(--borda)', paddingTop: 'var(--e-4)' }}>
          <div>
            <span style={{ fontWeight: 500 }}>Sessões ativas</span>
            <p className="texto-secundario" style={{ fontSize: 'var(--t-sm)' }}>
              Encerra o acesso em todos os dispositivos.
            </p>
          </div>
          <button type="button" className="botao botao-secundario" onClick={encerrarSessoes}>
            Encerrar todas
          </button>
        </div>
      </div>
    </section>
  );
}

export default SecuritySection;
