// Arquivo: frontend/src/components/TransactionModal/TransactionModal.jsx (VERSÃO FINAL SINCRONIZADA)
import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import './TransactionModal.css';

function TransactionModal({ onClose, onSaveSuccess }) {
  const [descricao, setDescricao] = useState('');
  const [valor, setValor] = useState('');
  const [categoriaId, setCategoriaId] = useState('');
  const [data, setData] = useState(new Date().toISOString().split('T')[0]); // Padrão: hoje
  const [observacoes, setObservacoes] = useState('');
  
  const [categorias, setCategorias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const fetchCategorias = async () => {
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
  }, []);

  // --- A MUDANÇA ESTÁ AQUI ---
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    try {
      // 1. Envia a transação (com a data)
      const response = await api.post('/transacoes/', {
        descricao: descricao,
        valor: parseFloat(valor),
        categoria_id: parseInt(categoriaId),
        data: data, // <-- A correção do fuso horário
        observacoes: observacoes,
      });

      setSuccess('Transação salva com sucesso!');
      
      // 2. Passa os novos dados do dashboard (que o backend retornou) para o "pai"
      setTimeout(() => {
        onSaveSuccess(response.data); // <-- A correção da condição de corrida
      }, 1000); 

    } catch (err) {
      console.error("Erro ao salvar transação:", err);
      setError("Erro ao salvar. Verifique os campos e tente novamente.");
    }
  };
  // ------------------------------

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