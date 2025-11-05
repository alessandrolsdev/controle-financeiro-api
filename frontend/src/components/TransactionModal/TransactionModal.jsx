// Arquivo: frontend/src/components/TransactionModal/TransactionModal.jsx
// Responsabilidade: O "Móvel" (componente) de formulário para criar transações.
// Esta é a versão final, com a lógica "Offline-First".

import React, { useState, useEffect } from 'react';
import api from '../../services/api'; // Nosso "mensageiro" axios
import './TransactionModal.css';

/**
 * Componente de Modal para Registrar uma Nova Transação.
 *
 * @param {object} props - Propriedades recebidas do "Pai" (Dashboard).
 * @param {function} props.onClose - Função a ser chamada para fechar o modal.
 * @param {function} props.onSaveSuccess - Função de "callback" a ser chamada
 * quando a transação for salva ONLINE, passando os novos dados
 * do dashboard de volta para o "Pai".
 */
function TransactionModal({ onClose, onSaveSuccess }) {
  // --- 1. Estados do Formulário ---
  const [descricao, setDescricao] = useState('');
  const [valor, setValor] = useState('');
  const [categoriaId, setCategoriaId] = useState('');
  const [data, setData] = useState(new Date().toISOString().split('T')[0]); // Padrão: data de hoje
  const [observacoes, setObservacoes] = useState('');
  
  // --- 2. Estados de UI (Interface) ---
  const [categorias, setCategorias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // --- 3. Efeito de Busca de Dados ---
  // Roda UMA VEZ assim que o modal é aberto.
  useEffect(() => {
    /** Busca a lista de categorias na API para preencher o dropdown. */
    const fetchCategorias = async () => {
      // Nota: Esta parte SÓ funciona se o usuário estiver ONLINE
      // ao abrir o modal. A V2.0 seria salvar as categorias no PWA.
      try {
        setLoading(true);
        const response = await api.get('/categorias/');
        setCategorias(response.data);
        if (response.data.length > 0) {
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
  }, []); // O [] garante que rode só uma vez.

  // --- 4. Função de Envio (COM LÓGICA ONLINE/OFFLINE) ---
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    // Prepara o "pacote" da transação que será salvo
    const transactionPayload = {
      descricao: descricao,
      valor: parseFloat(valor),
      categoria_id: parseInt(categoriaId),
      data: data,
      observacoes: observacoes,
    };

    // --- A MÁGICA DO PWA (PLANO A vs PLANO B) ---
    // Verificamos a API nativa do navegador para ver se há conexão
    if (navigator.onLine) {
      // --- PLANO A (ESTAMOS ONLINE) ---
      // O fluxo normal que já tínhamos.
      try {
        setSuccess('Salvando e sincronizando...');
        const response = await api.post('/transacoes/', transactionPayload);

        setSuccess('Transação salva com sucesso!');
        
        // Avisa o Dashboard (Pai) para atualizar os totais
        setTimeout(() => {
          onSaveSuccess(response.data); 
        }, 1000); 

      } catch (err) {
        console.error("Erro ao salvar transação (online):", err);
        setError("Erro ao salvar. Verifique os campos e tente novamente.");
      }
    } else {
      // --- PLANO B (ESTAMOS OFFLINE) ---
      // A internet caiu! Salvamos na "fila de espera" do localStorage.
      try {
        setSuccess('Salvando offline...');
        
        // 1. Pega a "fila" (queue) atual do localStorage, ou cria uma lista vazia
        const queue = JSON.parse(localStorage.getItem('offlineTransactionsQueue') || '[]');
        
        // 2. Adiciona o novo "pacote" (gasto) na fila
        queue.push(transactionPayload);
        
        // 3. Salva a fila atualizada de volta no localStorage
        localStorage.setItem('offlineTransactionsQueue', JSON.stringify(queue));

        setSuccess('Gasto salvo offline! Será sincronizado quando a internet voltar.');

        // 4. Apenas fecha o modal (não podemos atualizar o Dashboard)
        setTimeout(() => {
          onClose(); 
        }, 1500); // 1.5s para o usuário ler a msg
        
      } catch (err) {
        console.error("Erro ao salvar transação (offline):", err);
        setError("Não foi possível salvar offline. Tente novamente.");
      }
    }
  };
  
  // --- 5. Renderização do JSX (sem mudanças) ---
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Registrar Nova Transação</h2>
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
            <input type="number" id="valor" step="0.01" value={valor} onChange={(e) => setValor(e.target.value)} placeholder="0.00" required />
          </div>

          <div className="input-group">
            <label htmlFor="data">Data da Transação</label>
            <input type="date" id="data" value={data} onChange={(e) => setData(e.target.value)} required />
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
            Salvar Transação
          </button>
        </form>
      </div>
    </div>
  );
}

export default TransactionModal;