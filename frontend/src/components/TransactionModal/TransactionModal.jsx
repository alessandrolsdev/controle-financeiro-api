// Arquivo: frontend/src/components/TransactionModal/TransactionModal.jsx
// (VERSÃO V6.0 - MODO DE CRIAÇÃO/EDIÇÃO)
/*
REATORAÇÃO (Missão V6.0):
1. O modal agora aceita a prop 'transactionToEdit'.
2. Um estado 'isEditMode' é derivado dessa prop.
3. Os 'useState' (descricao, valor, etc.) agora são
   pré-preenchidos com os dados de 'transactionToEdit' se
   ele existir.
4. 'handleSubmit' foi REESCRITO:
   - Se 'isEditMode', ele chama 'api.put(...)'.
   - Se não, ele chama 'api.post(...)'.
5. O modo OFFLINE foi desabilitado para EDIÇÃO (mais seguro).
6. O Título e o Botão de Salvar mudam (ex: "Editar Transação").
*/

import React, { useState, useEffect } from 'react';
import api from '../../services/api'; 
import './TransactionModal.css';

// --- FUNÇÕES AUXILIARES ---

/**
 * Pega uma string ISO (do DB) ou 'undefined' (para novo)
 * e formata para o input 'datetime-local'.
 */
const formatToInput = (isoDate) => {
   // Usa a data passada ou a data de AGORA
   const d = isoDate ? new Date(isoDate) : new Date();
   
   // Formata como AAAA-MM-DDTHH:MM no fuso LOCAL
   const year = d.getFullYear();
   const month = (d.getMonth() + 1).toString().padStart(2, '0');
   const day = d.getDate().toString().padStart(2, '0');
   const hours = d.getHours().toString().padStart(2, '0');
   const minutes = d.getMinutes().toString().padStart(2, '0');
   
   return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/**
 * Limpa e converte uma string de dinheiro (ex: "R$ 1.234,56")
 * para um número que o 'parseFloat' entende (ex: "1234.56").
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
// -----------------------------


function TransactionModal({ onClose, onSaveSuccess, transactionToEdit }) {
  
  // 1. DETERMINA O MODO
  const isEditMode = Boolean(transactionToEdit);

  // 2. ESTADOS DO FORMULÁRIO (PRÉ-PREENCHIDOS)
  const [descricao, setDescricao] = useState(transactionToEdit?.descricao || '');
  const [valor, setValor] = useState(transactionToEdit?.valor.toString() || '');
  const [categoriaId, setCategoriaId] = useState(transactionToEdit?.categoria?.id || '');
  const [data, setData] = useState(formatToInput(transactionToEdit?.data)); // Usa o helper
  const [observacoes, setObservacoes] = useState(transactionToEdit?.observacoes || '');
  
  // --- Estados de UI (Sem mudança) ---
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
        
        // Se for MODO DE CRIAÇÃO e não houver categoria selecionada
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
  }, [isEditMode, categoriaId]); // Re-roda se o modo mudar

  // --- 4. Função de Envio (ATUALIZADA) ---
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    const valorNumerico = parseValor(valor);
    if (valorNumerico <= 0) {
      setError("O valor deve ser maior que zero.");
      return;
    }

    // O "pacote" de dados é o mesmo para criar ou editar
    const transactionPayload = {
      descricao: descricao,
      valor: valorNumerico,
      categoria_id: parseInt(categoriaId),
      data: data,
      observacoes: observacoes,
    };

    // --- A NOVA LÓGICA DE 'SAVE' ---
    if (navigator.onLine) {
      try {
        setSuccess(isEditMode ? 'Atualizando...' : 'Salvando...');
        
        if (isEditMode) {
          // --- MODO DE EDIÇÃO (PUT) ---
          await api.put(`/transacoes/${transactionToEdit.id}`, transactionPayload);
        } else {
          // --- MODO DE CRIAÇÃO (POST) ---
          await api.post('/transacoes/', transactionPayload);
        }

        setSuccess(isEditMode ? 'Transação atualizada com sucesso!' : 'Transação salva com sucesso!');
        
        // Avisa o Pai (MainLayout) para fechar e re-buscar os dados
        setTimeout(() => {
          onSaveSuccess(); 
        }, 1000); 

      } catch (err) {
        console.error("Erro ao salvar transação (online):", err);
        setError("Erro ao salvar. Verifique os campos e tente novamente.");
      }
    } else {
      // --- MODO OFFLINE ---
      if (isEditMode) {
        setError("A edição de transações não está disponível offline.");
        return;
      }
      
      // (Lógica de Fila Offline - apenas para Criação)
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
  
  // --- 5. Renderização do JSX (Títulos Dinâmicos) ---
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          {/* TÍTULO DINÂMICO */}
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
              max={formatToInput()} // Max = Agora
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

          {/* BOTÃO DINÂMICO */}
          <button type="submit" className="submit-button">
            {isEditMode ? 'Salvar Alterações' : 'Salvar Transação'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default TransactionModal;