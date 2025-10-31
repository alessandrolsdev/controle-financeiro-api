// Arquivo: frontend/src/components/TransactionModal/TransactionModal.jsx (VERSÃO FINAL)

import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import './TransactionModal.css';

// 1. O modal agora aceita DUAS props: onClose e onSaveSuccess
function TransactionModal({ onClose, onSaveSuccess }) {
  const [descricao, setDescricao] = useState('');
  const [valor, setValor] = useState('');
  const [categoriaId, setCategoriaId] = useState('');
  const [observacoes, setObservacoes] = useState('');
  const [categorias, setCategorias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Busca as categorias quando o modal abre (código que já tínhamos)
  useEffect(() => {
    const fetchCategorias = async () => {
      try {
        setLoading(true);
        const response = await api.get('/categorias/');
        setCategorias(response.data);
        // Define um valor padrão para o <select> se houver categorias
        if (response.data.length > 0) {
          setCategoriaId(response.data[0].id); // Seleciona a primeira categoria
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

  // 2. FUNÇÃO HANDLE SUBMIT (A GRANDE MUDANÇA)
  const handleSubmit = async (event) => {
    event.preventDefault(); // Impede o recarregamento da página
    setError(''); // Limpa erros antigos

    try {
      // 3. Envia os dados do formulário para o backend
      await api.post('/transacoes/', {
        descricao: descricao,
        valor: parseFloat(valor), // Converte o texto para número
        categoria_id: parseInt(categoriaId), // Converte o texto para número
        observacoes: observacoes,
      });

      // 4. SUCESSO! Avisa o Dashboard que salvou.
      onSaveSuccess();

    } catch (err) {
      console.error("Erro ao salvar transação:", err);
      setError("Erro ao salvar. Verifique os campos e tente novamente.");
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Registrar Nova Transação</h2>
          <button onClick={onClose} className="close-button">&times;</button>
        </div>
        
        {/* 5. Conecta o formulário à nossa função handleSubmit */}
        <form className="modal-form" onSubmit={handleSubmit}>
          {error && <p className="error-message">{error}</p>}

          <div className="input-group">
            <label htmlFor="descricao">Descrição</label>
            <input
              type="text"
              id="descricao"
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              placeholder="Ex: Diesel para a Retro 2"
              required
            />
          </div>

          <div className="input-group">
            <label htmlFor="valor">Valor (R$)</label>
            <input
              type="number"
              id="valor"
              step="0.01"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
              placeholder="0.00"
              required
            />
          </div>

          <div className="input-group">
            <label htmlFor="categoria">Categoria</label>
            <select 
              id="categoria"
              value={categoriaId}
              onChange={(e) => setCategoriaId(e.target.value)}
              required
            >
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
            <textarea
              id="observacoes"
              rows="3"
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
              placeholder="Ex: Placa do caminhão, local da compra..."
            ></textarea>
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