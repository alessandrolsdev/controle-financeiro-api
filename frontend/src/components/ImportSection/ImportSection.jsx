// Arquivo: frontend/src/components/ImportSection/ImportSection.jsx
/**
 * @file Importação de Planilhas.
 * @description Envia um arquivo CSV/XLSX e exibe o relatório da importação.
 */

import { useRef, useState } from 'react';
import { useOutletContext } from 'react-router-dom';

import api from '../../services/api';

/** Extensões aceitas, espelhando a allowlist do backend. */
const EXTENSOES = '.csv,.xlsx,.xlsm';

/** Limite de tamanho, verificado antes do envio para poupar o upload inteiro. */
const TAMANHO_MAXIMO = 5 * 1024 * 1024;

/**
 * Seção de importação de transações a partir de planilha.
 *
 * @returns {JSX.Element} A seção renderizada.
 */
function ImportSection() {
  const { dataInicioStr, dataFimStr, recarregarDashboard } = useOutletContext();

  const inputRef = useRef(null);
  const [arrastando, setArrastando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [relatorio, setRelatorio] = useState(null);
  const [erro, setErro] = useState('');

  /**
   * Envia o arquivo escolhido para a API.
   *
   * @param {File} arquivo - O arquivo selecionado.
   * @returns {Promise<void>} Conclui após o envio.
   */
  const enviar = async (arquivo) => {
    setErro('');
    setRelatorio(null);

    if (!arquivo) return;

    if (arquivo.size > TAMANHO_MAXIMO) {
      setErro('O arquivo excede o limite de 5 MB.');
      return;
    }

    const formulario = new FormData();
    formulario.append('arquivo', arquivo);

    setEnviando(true);

    try {
      const { data } = await api.post('/transacoes/importar', formulario, {
        params: { data_inicio: dataInicioStr, data_fim: dataFimStr },
      });

      setRelatorio(data);

      // O dashboard do layout precisa refletir os lançamentos recém-criados.
      if (data.importadas > 0 && recarregarDashboard) {
        recarregarDashboard();
      }
    } catch (err) {
      setErro(
        err.response?.data?.detail ||
          'Não foi possível importar o arquivo. Verifique o formato e tente de novo.'
      );
    } finally {
      setEnviando(false);
      // Permite reenviar o mesmo arquivo depois de uma correção.
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  /**
   * Trata o arquivo solto na área de arrastar.
   *
   * @param {React.DragEvent} evento - O evento de drop.
   */
  const aoSoltar = (evento) => {
    evento.preventDefault();
    setArrastando(false);
    enviar(evento.dataTransfer.files?.[0]);
  };

  return (
    <section className="config-secao">
      <header>
        <h2>Importar transações</h2>
        <p>
          Envie um extrato ou planilha e o sistema classifica os lançamentos
          automaticamente.
        </p>
      </header>

      <div className="config-corpo">
        {erro && <p className="mensagem mensagem-erro">{erro}</p>}

        <div
          className={arrastando ? 'importar-area arrastando' : 'importar-area'}
          onDragOver={(e) => {
            e.preventDefault();
            setArrastando(true);
          }}
          onDragLeave={() => setArrastando(false)}
          onDrop={aoSoltar}
        >
          <p>Arraste o arquivo aqui ou escolha do computador.</p>

          <input
            ref={inputRef}
            type="file"
            accept={EXTENSOES}
            onChange={(e) => enviar(e.target.files?.[0])}
            className="apenas-leitor-de-tela"
            id="arquivo-importacao"
          />

          <button
            type="button"
            className="botao botao-secundario"
            onClick={() => inputRef.current?.click()}
            disabled={enviando}
          >
            {enviando ? 'Processando…' : 'Escolher arquivo'}
          </button>

          <span className="importar-dica">
            CSV ou XLSX, até 5 MB. Colunas necessárias: data, descrição e valor.
          </span>
        </div>

        {relatorio && (
          <div className="importar-relatorio">
            <p
              className={
                relatorio.importadas > 0
                  ? 'mensagem mensagem-sucesso'
                  : 'mensagem mensagem-erro'
              }
            >
              {relatorio.importadas} transação(ões) importada(s)
              {relatorio.ignoradas > 0 && `, ${relatorio.ignoradas} ignorada(s)`}.
            </p>

            {relatorio.erros.length > 0 && (
              <ul className="importar-erros">
                {relatorio.erros.map((item) => (
                  <li key={`${item.linha}-${item.motivo}`}>
                    <span className="linha">Linha {item.linha}</span>
                    <span>{item.motivo}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export default ImportSection;
