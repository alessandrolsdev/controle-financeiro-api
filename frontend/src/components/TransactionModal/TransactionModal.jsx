// Arquivo: frontend/src/components/TransactionModal/TransactionModal.jsx
// Responsabilidade: O "Móvel" (componente) de formulário para criar transações.
//
// Este é um componente "Filho" do Dashboard. Ele não gerencia o estado global,
// ele apenas:
// 1. Gerencia o estado do *seu próprio* formulário (o que o usuário digita).
// 2. Busca as categorias da API quando é aberto.
// 3. Envia a nova transação para a API.
// 4. "Avisa" o "Pai" (Dashboard) que o salvamento foi um sucesso.

import React, { useState, useEffect } from 'react';
import api from '../../services/api'; // Nosso "mensageiro" axios
import './TransactionModal.css';

/**
 * Componente de Modal para Registrar uma Nova Transação.
 *
 * @param {object} props - Propriedades recebidas do componente "Pai" (Dashboard).
 * @param {function} props.onClose - Função a ser chamada para fechar o modal.
 * @param {function} props.onSaveSuccess - Função de "callback" a ser chamada
 * quando a transação for salva, passando os novos dados
 * do dashboard de volta para o "Pai".
 */
function TransactionModal({ onClose, onSaveSuccess }) {
  // --- 1. Estados do Formulário ---
  // Controla os valores dos campos de input
  const [descricao, setDescricao] = useState('');
  const [valor, setValor] = useState('');
  const [categoriaId, setCategoriaId] = useState(''); // Armazena o ID da categoria selecionada
  const [data, setData] = useState(new Date().toISOString().split('T')[0]); // Padrão: data de hoje
  const [observacoes, setObservacoes] = useState('');
  
  // --- 2. Estados de UI (Interface) ---
  const [categorias, setCategorias] = useState([]); // Armazena a lista de categorias do dropdown
  const [loading, setLoading] = useState(true); // Controla o "Carregando..." do dropdown
  const [error, setError] = useState('');       // Mensagem de erro do formulário
  const [success, setSuccess] = useState('');     // Mensagem de sucesso do formulário

  // --- 3. Efeito de Busca de Dados ---
  // Roda UMA VEZ (devido ao '[]') assim que o modal é montado/aberto.
  useEffect(() => {
    /** Busca a lista de categorias na API para preencher o dropdown. */
    const fetchCategorias = async () => {
      try {
        setLoading(true);
        const response = await api.get('/categorias/');
        setCategorias(response.data);
        // Seleciona automaticamente a primeira categoria da lista
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
  }, []); // O array de dependência vazio '[]' é o que garante que isso rode só uma vez.

  // --- 4. Função de Envio (Ação Principal) ---
  /**
   * Lida com o envio do formulário quando o usuário clica em "Salvar Transação".
   */
  const handleSubmit = async (event) => {
    event.preventDefault(); // Impede o recarregamento padrão do navegador
    setError('');
    setSuccess('');

    try {
      // 1. Envia a nova transação para o backend.
      // O backend (main.py) foi programado para, em vez de um "OK",
      // responder com os NOVOS TOTAIS DO DASHBOARD.
      const response = await api.post('/transacoes/', {
        descricao: descricao,
        valor: parseFloat(valor), // Converte o texto "150.00" para o número 150.00
        categoria_id: parseInt(categoriaId), // Converte o ID para número
        data: data, // Envia a data local (Correção do Bug de Fuso Horário)
        observacoes: observacoes,
      });

      // 2. Mostra um feedback visual de sucesso
      setSuccess('Transação salva com sucesso!');
      
      // 3. A "Bala de Prata" (Correção do Bug de Atualização)
      // Espera 1 segundo (para o usuário ler a msg de sucesso) e então...
      setTimeout(() => {
        // ...chama a função 'onSaveSuccess' (que veio do "Pai")
        // e "entrega" os novos dados do dashboard (response.data) para ele.
        onSaveSuccess(response.data); 
      }, 1000); 

    } catch (err) {
      console.error("Erro ao salvar transação:", err);
      setError("Erro ao salvar. Verifique os campos e tente novamente.");
    }
  };
  
  // --- 5. Renderização do JSX ---
  return (
    // O 'modal-overlay' é o fundo escuro.
    // 'onClose' é chamado se o usuário clicar FORA do modal.
    <div className="modal-overlay" onClick={onClose}>
      
      {/* O 'modal-content' é a caixa branca no meio.
          'e.stopPropagation()' é um truque profissional que impede
          que um clique DENTRO da caixa se propague para o 'overlay'
          e feche o modal acidentalmente. */}
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        
        <div className="modal-header">
          <h2>Registrar Nova Transação</h2>
          <button onClick={onClose} className="close-button">&times;</button>
        </div>
        
        <form className="modal-form" onSubmit={handleSubmit}>
          {/* Mensagens de feedback */}
          {error && <p className="error-message">{error}</p>}
          {success && <p className="success-message">{success}</p>}

          {/* Campos do formulário controlados pelo 'useState' */}
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
              {/* Loop (map) para preencher o dropdown com as categorias da API */}
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