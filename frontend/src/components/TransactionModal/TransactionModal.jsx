// Arquivo: frontend/src/components/TransactionModal/TransactionModal.jsx
/**
 * @file Modal de Transação (Criação e Edição).
 * @description Componente de formulário para criar, editar e gerenciar transações financeiras, com suporte a operação offline.
 */

import { useState, useEffect } from 'react';
import api from '../../services/api';
import './TransactionModal.css';

/**
 * Formata uma data para o formato aceito pelo input datetime-local.
 * @param {Date | string | null} isoDate - A data a ser formatada. Se nulo, usa a data atual.
 * @returns {string} A string de data formatada (AAAA-MM-DDTHH:MM).
 */
const formatToInput = (isoDate) => {
   const d = isoDate ? new Date(isoDate) : new Date();
   
   const fusoHorarioLocal = d.getTimezoneOffset() * 60000;
   const dataLocal = new Date(d.valueOf() - fusoHorarioLocal);
   
   return dataLocal.toISOString().slice(0, 16);
}

/**
 * Converte uma string de valor monetário para float.
 * Trata formatos com vírgula ou ponto decimal.
 * @param {string} valorString - A string representando o valor.
 * @returns {number} O valor numérico.
 */
const parseValor = (valorString) => {
  if (!valorString) return 0.0;
  
  let limpo = valorString.toString().replace(/[^0-9,.-]/g, ''); 
  
  if (limpo.includes(',')) {
    limpo = limpo.replace(/\./g, '');
    limpo = limpo.replace(',', '.');
  }
  
  return parseFloat(limpo) || 0.0;
};

/**
 * Componente Modal para Transações.
 *
 * Permite criar novas transações ou editar existentes. Suporta operação offline para criação,
 * armazenando dados no localStorage para sincronização posterior.
 *
 * @param {object} props
 * @param {function} props.onClose - Função para fechar o modal.
 * @param {function} props.onSaveSuccess - Callback executado após salvar com sucesso (recebe dados atualizados).
 * @param {object | null} props.transactionToEdit - Objeto da transação para edição (null para criação).
 * @param {string} props.dataInicioStr - Data de início do filtro atual (para recálculo do dashboard).
 * @param {string} props.dataFimStr - Data de fim do filtro atual (para recálculo do dashboard).
 * @returns {JSX.Element} O modal renderizado.
 */
function TransactionModal({ 
  onClose, 
  onSaveSuccess, 
  transactionToEdit,
  dataInicioStr, 
  dataFimStr     
}) {
  const isEditMode = Boolean(transactionToEdit);

  // --- Estados do Formulário ---
  const [descricao, setDescricao] = useState(transactionToEdit?.descricao || '');
  const [valor, setValor] = useState(transactionToEdit?.valor.toString() || '');
  const [categoriaId, setCategoriaId] = useState(transactionToEdit?.categoria?.id || '');
  const [data, setData] = useState(formatToInput(transactionToEdit?.data));
  const [observacoes, setObservacoes] = useState(transactionToEdit?.observacoes || '');
  
  // --- Estados de UI ---
  const [categorias, setCategorias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  /**
   * Efeito colateral para carregar categorias.
   * Executa ao abrir o modal. Preenche a categoria padrão se estiver em modo de criação.
   */
  useEffect(() => {
    const fetchCategorias = async () => {
      try {
        setLoading(true);
        const response = await api.get('/categorias/');
        setCategorias(response.data);
        
        if (!isEditMode && response.data.length > 0 && !categoriaId) {
          setCategoriaId(response.data[0].id);
        }
        
        setLoading(false);
      } catch (err) {
        console.error("Erro ao buscar categorias para o modal:", err);
        setError('Não foi possível carregar as categorias.');
        setLoading(false);
      }
    };
    fetchCategorias();
  }, [isEditMode, categoriaId]);

  /**
   * Manipula o envio do formulário.
   *
   * Valida os dados, constrói o payload e decide entre envio online ou armazenamento offline.
   * Em modo online, realiza a requisição POST ou PUT e chama o callback de sucesso.
   * Em modo offline (apenas criação), salva na fila local.
   *
   * @param {Event} event - O evento de submit do formulário.
   */
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    const valorNumerico = parseValor(valor);
    if (valorNumerico <= 0) {
      setError("O valor deve ser maior que zero.");
      return;
    }

    const transactionPayload = {
      descricao: descricao,
      valor: valorNumerico,
      categoria_id: parseInt(categoriaId),
      data: data,
      observacoes: observacoes,
    };

    // --- Lógica Online ---
    if (navigator.onLine) {
      try {
        setSuccess(isEditMode ? 'Atualizando...' : 'Salvando e sincronizando...');
        
        let response;
        
        const recalculateParams = {
            data_inicio: dataInicioStr,
            data_fim: dataFimStr
        };
        
        if (isEditMode) {
          response = await api.put(
            `/transacoes/${transactionToEdit.id}`, 
            transactionPayload,
            { params: recalculateParams }
          );
        } else {
          response = await api.post(
            '/transacoes/', 
            transactionPayload,
            { params: recalculateParams }
          );
        }

        setSuccess(isEditMode ? 'Transação atualizada com sucesso!' : 'Transação salva com sucesso!');
        
        setTimeout(() => {
          onSaveSuccess(response.data); 
        }, 1000);

      } catch (err) {
        console.error("Erro ao salvar transação (online):", err);
        setError("Erro ao salvar. Verifique os campos e tente novamente.");
        setSuccess('');
      }
    } else {
      // --- Lógica Offline ---
      if (isEditMode) {
        setError("A edição de transações não está disponível offline.");
        return;
      }
      
      try {
        setSuccess('Salvando offline...');

        const queue = JSON.parse(localStorage.getItem('offlineTransactionsQueue') || '[]');

        /*
         * A chave de idempotência é gerada AQUI, no momento em que o
         * lançamento entra na fila — e não na hora do envio. Assim ela
         * sobrevive a recargas da página e a tentativas repetidas de
         * sincronização, e o backend reconhece o reenvio como o mesmo
         * lançamento em vez de criar um segundo débito.
         */
        queue.push({
          ...transactionPayload,
          chaveIdempotencia: crypto.randomUUID(),
          periodo: { data_inicio: dataInicioStr, data_fim: dataFimStr },
        });

        localStorage.setItem('offlineTransactionsQueue', JSON.stringify(queue));

        setSuccess('Lançamento salvo offline! Será sincronizado quando a internet voltar.');
        
        setTimeout(() => {
           onClose(); 
        }, 1500);
        
      } catch (err) {
        console.error("Erro ao salvar transação (offline):", err);
        setError("Não foi possível salvar offline. Tente novamente.");
        setSuccess('');
      }
    }
  };
  
  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-modal"
      >
        <div className="modal-header">
          <h2 id="titulo-modal">
            {isEditMode ? 'Editar transação' : 'Nova transação'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="close-button"
            aria-label="Fechar"
          >
            &times;
          </button>
        </div>

        <form className="modal-form" onSubmit={handleSubmit} id="form-transacao">
          {error && <p className="mensagem mensagem-erro">{error}</p>}
          {success && <p className="mensagem mensagem-sucesso">{success}</p>}

          <div>
            <label className="rotulo" htmlFor="descricao">
              Descrição
            </label>
            <input
              type="text"
              id="descricao"
              className="campo"
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              placeholder="Mercado, combustível, salário…"
              maxLength={255}
              required
              autoFocus
            />
          </div>

          <div className="modal-linha">
            <div>
              <label className="rotulo" htmlFor="valor">
                Valor (R$)
              </label>
              <input
                type="text"
                inputMode="decimal"
                id="valor"
                className="campo"
                value={valor}
                onChange={(e) => setValor(e.target.value)}
                placeholder="0,00"
                required
              />
            </div>

            <div>
              <label className="rotulo" htmlFor="data">
                Data e hora
              </label>
              <input
                type="datetime-local"
                id="data"
                className="campo"
                value={data}
                onChange={(e) => setData(e.target.value)}
                max={formatToInput()}
                required
              />
            </div>
          </div>

          <div>
            <label className="rotulo" htmlFor="categoria">
              Categoria
            </label>
            <select
              id="categoria"
              className="campo"
              value={categoriaId}
              onChange={(e) => setCategoriaId(e.target.value)}
              required
              disabled={loading}
            >
              <option value="" disabled>
                {loading ? 'Carregando…' : 'Selecione'}
              </option>
              {!loading &&
                categorias.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.nome} · {cat.tipo === 'Receita' ? 'Receita' : 'Despesa'}
                  </option>
                ))}
            </select>
          </div>

          <div>
            <label className="rotulo" htmlFor="observacoes">
              Observações
            </label>
            <textarea
              id="observacoes"
              className="campo"
              rows="3"
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
              placeholder="Opcional"
              maxLength={2000}
            />
          </div>
        </form>

        <div className="modal-rodape">
          <button type="button" className="botao botao-secundario" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="submit"
            form="form-transacao"
            className="botao botao-primario"
            disabled={loading || Boolean(success)}
          >
            {isEditMode ? 'Salvar' : 'Adicionar'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default TransactionModal;
