// Arquivo: frontend/src/components/TransactionModal/TransactionModal.jsx
/*
 * Componente de Modal de Transação (O "Formulário Inteligente").
 *
 * Este é um dos componentes mais complexos do frontend.
 * Ele gerencia a UI e a lógica para CRIAR, EDITAR e
 * salvar transações OFFLINE.
 *
 * Ele é 100% "controlado" pelo 'MainLayout.jsx' (Pai).
 */

import React, { useState, useEffect } from 'react';
import api from '../../services/api'; // Nosso "embaixador" axios
import './TransactionModal.css';

// --- Funções Auxiliares (Helpers) de Data e Valor ---

/**
 * Formata uma data (objeto Date ou string ISO) para a string 'AAAA-MM-DDTHH:MM'
 * que o input 'datetime-local' exige.
 * Se 'isoDate' for nulo (Modo de Criação), usa a data/hora atual.
 */
const formatToInput = (isoDate) => {
   // Usa a data passada ou a data de AGORA
   const d = isoDate ? new Date(isoDate) : new Date();
   
   // (Corrige o fuso horário para 'datetime-local')
   const fusoHorarioLocal = d.getTimezoneOffset() * 60000;
   const dataLocal = new Date(d.valueOf() - fusoHorarioLocal);
   
   // Retorna os primeiros 16 caracteres (AAAA-MM-DDTHH:MM)
   return dataLocal.toISOString().slice(0, 16);
}

/**
 * Limpa e converte uma string de dinheiro (ex: "R$ 1.234,56" ou "12,34")
 * para um número float que o 'parseFloat' entende (ex: 1234.56).
 * (V2.8)
 */
const parseValor = (valorString) => {
  if (!valorString) return 0.0;
  
  // 1. Remove tudo que NÃO é número, vírgula ou ponto
  let limpo = valorString.toString().replace(/[^0-9,.-]/g, ''); 
  
  // 2. Se houver vírgula, assume que é o decimal (padrão BR)
  if (limpo.includes(',')) {
    limpo = limpo.replace(/\./g, ''); // Remove pontos (milhares)
    limpo = limpo.replace(',', '.'); // Troca vírgula (decimal) por ponto
  }
  
  return parseFloat(limpo) || 0.0;
};
// ---------------------------------------------------


/**
 * Renderiza o modal de Criar/Editar Transação.
 *
 * @param {object} props
 * @param {function} props.onClose - (Do Pai) Função para fechar o modal.
 * @param {function} props.onSaveSuccess - (Do Pai) Callback síncrono que passa
 * os dados atualizados do dashboard.
 * @param {object | null} props.transactionToEdit - (Do Pai) Se for um objeto,
 * o modal entra em "Modo de Edição". Se for 'null', entra em "Modo de Criação".
 * @param {string} props.dataInicioStr - (Do Pai) Data de início do filtro (AAAA-MM-DD).
 * @param {string} props.dataFimStr - (Do Pai) Data de fim do filtro (AAAA-MM-DD).
 */
function TransactionModal({ 
  onClose, 
  onSaveSuccess, 
  transactionToEdit,
  dataInicioStr, 
  dataFimStr     
}) {
  
  // --- 1. Determina o Modo ---
  const isEditMode = Boolean(transactionToEdit); // True se 'transactionToEdit' não for nulo

  // --- 2. Estados do Formulário (Pré-preenchidos se 'isEditMode') ---
  const [descricao, setDescricao] = useState(transactionToEdit?.descricao || '');
  const [valor, setValor] = useState(transactionToEdit?.valor.toString() || '');
  const [categoriaId, setCategoriaId] = useState(transactionToEdit?.categoria?.id || '');
  const [data, setData] = useState(formatToInput(transactionToEdit?.data));
  const [observacoes, setObservacoes] = useState(transactionToEdit?.observacoes || '');
  
  // --- 3. Estados de UI (Dropdown e Feedback) ---
  const [categorias, setCategorias] = useState([]);
  const [loading, setLoading] = useState(true); // Loading do dropdown de categorias
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(''); // (Usado para o feedback "Salvando...")

  /**
   * Efeito [onLoad]: Busca as Categorias.
   * Roda UMA VEZ assim que o modal é aberto.
   */
  useEffect(() => {
    const fetchCategorias = async () => {
      try {
        setLoading(true);
        const response = await api.get('/categorias/');
        setCategorias(response.data);
        
        // Se for MODO DE CRIAÇÃO e nenhuma categoria estiver
        // selecionada, seleciona a primeira da lista por padrão.
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
  }, [isEditMode, categoriaId]); // (Depende de 'isEditMode' para lógica de seleção)

  
  /**
   * Função de Envio (Handle Submit - Lógica Síncrona V-Revert).
   * Lida com a lógica Online (Plano A) e Offline (Plano B).
   */
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    // Validação do valor (V2.8)
    const valorNumerico = parseValor(valor);
    if (valorNumerico <= 0) {
      setError("O valor deve ser maior que zero.");
      return;
    }

    // O "pacote" de dados para a API (mesmo para Criar ou Editar)
    const transactionPayload = {
      descricao: descricao,
      valor: valorNumerico,
      categoria_id: parseInt(categoriaId),
      data: data, // (Já está no formato 'datetime-local' AAAA-MM-DDTHH:MM)
      observacoes: observacoes,
    };

    // --- PLANO A (ONLINE) ---
    if (navigator.onLine) {
      try {
        setSuccess(isEditMode ? 'Atualizando...' : 'Salvando e sincronizando...');
        
        let response; // A resposta da API (que conterá o DashboardData)
        
        // Parâmetros para o recálculo síncrono do backend
        const recalculateParams = {
            data_inicio: dataInicioStr,
            data_fim: dataFimStr
        };
        
        if (isEditMode) {
          // --- MODO DE EDIÇÃO (PUT) ---
          response = await api.put(
            `/transacoes/${transactionToEdit.id}`, 
            transactionPayload,
            { params: recalculateParams } // Envia as datas do filtro
          );
        } else {
          // --- MODO DE CRIAÇÃO (POST) ---
          response = await api.post(
            '/transacoes/', 
            transactionPayload,
            { params: recalculateParams } // Envia as datas do filtro
          );
        }

        // A 'response.data' é o OBJETO DASHBOARD COMPLETO
        setSuccess(isEditMode ? 'Transação atualizada com sucesso!' : 'Transação salva com sucesso!');
        
        // Passa os dados do dashboard atualizados de volta para o Pai (MainLayout)
        setTimeout(() => {
          onSaveSuccess(response.data); 
        }, 1000); // (1s de delay para o usuário ler a msg)

      } catch (err) {
        console.error("Erro ao salvar transação (online):", err);
        setError("Erro ao salvar. Verifique os campos e tente novamente.");
        setSuccess(''); // Limpa o "Salvando..."
      }
    } else {
      // --- PLANO B (OFFLINE - SÓ FUNCIONA PARA CRIAÇÃO) ---
      if (isEditMode) {
        setError("A edição de transações não está disponível offline.");
        return;
      }
      
      try {
        setSuccess('Salvando offline...');
        
        // 1. Pega a "fila" (queue) atual do localStorage
        const queue = JSON.parse(localStorage.getItem('offlineTransactionsQueue') || '[]');
        
        // 2. Adiciona o novo "pacote" (gasto) na fila
        queue.push(transactionPayload);
        
        // 3. Salva a fila atualizada de volta no localStorage
        localStorage.setItem('offlineTransactionsQueue', JSON.stringify(queue));

        setSuccess('Gasto salvo offline! Será sincronizado quando a internet voltar.');
        
        // (V9.3) A fila será pega pelo 'AuthContext'
        // quando o app voltar a ficar online.
        
        // 4. Apenas fecha o modal
        setTimeout(() => {
           onClose(); 
        }, 1500); // (1.5s para o usuário ler a msg)
        
      } catch (err) {
        console.error("Erro ao salvar transação (offline):", err);
        setError("Não foi possível salvar offline. Tente novamente.");
        setSuccess('');
      }
    }
  };
  
  
  return (
    // 'onClick={onClose}' no overlay permite fechar clicando fora
    <div className="modal-overlay" onClick={onClose}>
      
      {/* 'e.stopPropagation()' impede que o clique
         DENTRO do modal feche o modal */}
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        
        <div className="modal-header">
          {/* Título Dinâmico (V6.0) */}
          <h2>{isEditMode ? 'Editar Transação' : 'Registrar Nova Transação'}</h2>
          <button onClick={onClose} className="close-button">&times;</button>
        </div>
        
        <form className="modal-form" onSubmit={handleSubmit}>
          {/* Feedback de Erro/Sucesso */}
          {error && <p className="error-message">{error}</p>}
          {success && <p className="success-message">{success}</p>}

          <div className="input-group">
            <label htmlFor="descricao">Descrição</label>
            <input type="text" id="descricao" value={descricao} onChange={(e) => setDescricao(e.target.value)} placeholder="Ex: Diesel para a Retro 2" required />
          </div>

          <div className="input-group">
            <label htmlFor="valor">Valor (R$)</label>
            <input 
              type="text" // (V2.8) 'text' para aceitar vírgula (,)
              inputMode="decimal" // (V2.8) Teclado numérico no mobile
              id="valor" 
              value={valor} 
              onChange={(e) => setValor(e.target.value)} 
              placeholder="0,00" 
              required 
            />
          </div>

          <div className="input-group">
            <label htmlFor="data">Data e Hora da Transação</label>
            <input 
              type="datetime-local" // (V2.2)
              id="data" 
              value={data} 
              onChange={(e) => setData(e.target.value)} 
              required 
              max={formatToInput()} // (V2.10) Impede datas futuras
            />
          </div>

          <div className="input-group">
            <label htmlFor="categoria">Categoria</label>
            <select id="categoria" value={categoriaId} onChange={(e) => setCategoriaId(e.target.value)} required disabled={loading}>
              <option value="" disabled>
                {loading ? "Carregando..." : "Selecione uma categoria"}
              </option>
              {!loading && categorias.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.nome} ({cat.tipo})
                </option>
              ))}
            </select>
          </div>

          <div className="input-group">
            <label htmlFor="observacoes">Observações (Opcional)</label>
            <textarea id="observacoes" rows="3" value={observacoes} onChange={(e) => setObservacoes(e.target.value)} placeholder="Ex: Placa do caminhão..."></textarea>
          </div>

          {/* Botão Dinâmico (V6.0) */}
          {/* (Desabilitado se estiver carregando OU se houver msg de sucesso) */}
          <button type="submit" className="submit-button" disabled={loading || success}>
            {isEditMode ? 'Salvar Alterações' : 'Salvar Transação'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default TransactionModal;