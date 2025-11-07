// Arquivo: frontend/src/components/TransactionModal/TransactionModal.jsx
// (VERSÃO V-REVERTIDA - SÍNCRONA/GRATUITA)
/*
REVERSÃO (MISSÃO DE DEPLOY GRATUITO):
1. Aceita 'dataInicioStr' e 'dataFimStr' como props (do MainLayout).
2. 'handleSubmit' agora envia esses dados como 'params'
   para o backend, para que ele possa recalcular o dashboard.
3. 'onSaveSuccess(response.data)' é chamado, enviando os
   dados do dashboard (recebidos da API) de volta para o Pai.
*/

import React, { useState, useEffect } from 'react';
import api from '../../services/api'; 
import './TransactionModal.css';

// --- FUNÇÕES AUXILIARES ---
const formatToInput = (isoDate) => {
   const d = isoDate ? new Date(isoDate) : new Date();
   const year = d.getFullYear();
   const month = (d.getMonth() + 1).toString().padStart(2, '0');
   const day = d.getDate().toString().padStart(2, '0');
   const hours = d.getHours().toString().padStart(2, '0');
   const minutes = d.getMinutes().toString().padStart(2, '0');
   return `${year}-${month}-${day}T${hours}:${minutes}`;
}
const parseValor = (valorString) => {
  if (!valorString) return 0.0;
  let limpo = valorString.toString().replace(/[^0-9,.-]/g, ''); 
  if (limpo.includes(',')) {
    limpo = limpo.replace(/\./g, '');
    limpo = limpo.replace(',', '.');
  }
  return parseFloat(limpo) || 0.0;
};
// -----------------------------


function TransactionModal({ 
  onClose, 
  onSaveSuccess, 
  transactionToEdit,
  dataInicioStr, // <-- NOVO PROP
  dataFimStr     // <-- NOVO PROP
}) {
  
  const isEditMode = Boolean(transactionToEdit);

  // --- Estados do Formulário (Pré-preenchidos) ---
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

  // --- Efeito de Busca de Dados (Categorias) ---
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

  // --- Função de Envio (REVERTIDA) ---
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

    // (Ainda desabilitamos o modo offline para edição)
    if (isEditMode && !navigator.onLine) {
        setError("A edição de transações não está disponível offline.");
        return;
    }
    
    // MUDANÇA: Prepara os 'params' para o recálculo síncrono
    const recalculateParams = {
        data_inicio: dataInicioStr,
        data_fim: dataFimStr
    };

    // --- LÓGICA DE 'SAVE' SÍNCRONA ---
    if (navigator.onLine) {
      try {
        setSuccess(isEditMode ? 'Atualizando...' : 'Salvando...');
        
        let response; // A resposta da API
        
        if (isEditMode) {
          // --- MODO DE EDIÇÃO (PUT) ---
          response = await api.put(
            `/transacoes/${transactionToEdit.id}`, 
            transactionPayload,
            { params: recalculateParams } // <-- Envia as datas do filtro
          );
        } else {
          // --- MODO DE CRIAÇÃO (POST) ---
          response = await api.post(
            '/transacoes/', 
            transactionPayload,
            { params: recalculateParams } // <-- Envia as datas do filtro
          );
        }

        // A 'response.data' agora é o OBJETO DASHBOARD COMPLETO
        setSuccess(isEditMode ? 'Transação atualizada com sucesso!' : 'Transação salva com sucesso!');
        
        // MUDANÇA: Passa os dados do dashboard (response.data)
        // de volta para o Pai (MainLayout)
        setTimeout(() => {
          onSaveSuccess(response.data); 
        }, 1000); 

      } catch (err) {
        console.error("Erro ao salvar transação (online):", err);
        setError("Erro ao salvar. Verifique os campos e tente novamente.");
      }
    } else {
      // --- MODO OFFLINE (Apenas Criação) ---
      // (Esta lógica permanece a mesma)
      try {
        setSuccess('Salvando offline...');
        const queue = JSON.parse(localStorage.getItem('offlineTransactionsQueue') || '[]');
        queue.push(transactionPayload);
        localStorage.setItem('offlineTransactionsQueue', JSON.stringify(queue));
        setSuccess('Gasto salvo offline! Será sincronizado quando a internet voltar.');
        setTimeout(() => {
           onClose(); 
        }, 1500);
      } catch (err) {
        console.error("Erro ao salvar transação (offline):", err);
        setError("Não foi possível salvar offline. Tente novamente.");
      }
    }
  };
  
  // --- JSX (Sem mudança) ---
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{isEditMode ? 'Editar Transação' : 'Registrar Nova Transação'}</h2>
          <button onClick={onClose} className="close-button">&times;</button>
        </div>
        
        <form className="modal-form" onSubmit={handleSubmit}>
          {error && <p className="error-message">{error}</p>}
          {success && <p className="success-message">{success}</p>}

          <div className="input-group">
            <label htmlFor="descricao">Descrição</label>
            <input type="text" id="descricao" value={descricao} onChange={(e) => setDescricao(e.target.value)} placeholder="Ex: Diesel para a Retro 2" required />
          </div>

          <div className="input-group">
            <label htmlFor="valor">Valor (R$)</label>
            <input 
              type="text"
              inputMode="decimal"
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
              type="datetime-local"
              id="data" 
              value={data} 
              onChange={(e) => setData(e.target.value)} 
              required 
              max={formatToInput()}
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

          <button type="submit" className="submit-button">
            {isEditMode ? 'Salvar Alterações' : 'Salvar Transação'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default TransactionModal;