// Arquivo: frontend/src/pages/Dashboard/Dashboard.jsx
// Responsabilidade: "Página" (cômodo) principal.
// Este é o componente "Pai" que renderiza:
// 1. Os cards de resumo (Total Gastos, Lucro, etc.)
// 2. O botão "+ Registrar Transação"
// 3. O componente "Filho" <TransactionModal> (quando ele está aberto)

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext'; // Hook para o "cérebro" do login
import { Link } from 'react-router-dom'; // Para o link de "Configurações"
import api from '../../services/api'; // Nosso "mensageiro" axios
import './Dashboard.css';
import TransactionModal from '../../components/TransactionModal/TransactionModal'; // O "filho"

/**
 * Componente da página principal do Dashboard.
 * Gerencia o estado dos dados financeiros e a visibilidade do modal.
 */
function Dashboard() {
  // --- Hooks de Estado ---
  const { logout } = useAuth(); // Função de logout do cérebro global
  const [data, setData] = useState(null); // Armazena os dados vindos do /dashboard/ (ex: { total_gastos: 150.00, ... })
  const [loading, setLoading] = useState(true); // Controla a exibição de "Carregando..."
  const [error, setError] = useState(''); // Armazena mensagens de erro da API
  const [isModalOpen, setIsModalOpen] = useState(false); // Controla se o modal está aberto ou fechado

  // --- Lógica de Busca de Dados ---

  /**
   * Função principal que busca os dados do backend.
   * É chamada quando a página carrega e quando uma nova transação é salva.
   */
  const fetchDashboardData = async () => {
    // Define o período padrão (últimos 30 dias)
    const dataFim = new Date().toISOString().split('T')[0]; // Hoje
    const dataInicio = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
      .toISOString()
      .split('T')[0]; // 30 dias atrás

    try {
      setLoading(true); // Mostra o "Carregando..."
      const response = await api.get('/dashboard/', {
        params: { data_inicio: dataInicio, data_fim: dataFim },
      });
      setData(response.data); // Salva os dados no estado 'data'
      setLoading(false); // Esconde o "Carregando..."
    } catch (err) {
      console.error('Erro ao buscar dados do dashboard:', err);
      setError('Não foi possível carregar os dados.');
      setLoading(false);
    }
  };

  // Efeito "On Mount": Roda UMA VEZ quando o componente é carregado.
  // Chama a função para buscar os dados iniciais.
  useEffect(() => {
    fetchDashboardData();
  }, []); // O [] garante que rode só uma vez

  // --- Lógica de Callback (Pai/Filho) ---

  /**
   * Esta função é o "Callback" que é passado como prop para o <TransactionModal>.
   * O Modal (filho) chama esta função quando o salvamento é bem-sucedido.
   * @param {object} novosDadosDoDashboard - Os dados atualizados do dashboard,
   * retornados diretamente pela API 'POST /transacoes/'.
   */
  const handleSaveSuccess = (novosDadosDoDashboard) => {
    setIsModalOpen(false); // 1. Fecha o modal
    setData(novosDadosDoDashboard); // 2. ATUALIZA O ESTADO com os novos dados
                                    //    (Isso evita uma segunda chamada de API e previne bugs)
  };

  // --- Renderização Condicional ---

  /**
   * Renderiza o conteúdo principal (cards) com base no estado (loading, error, data).
   */
  const renderContent = () => {
    if (loading) { return <p>Carregando dados...</p>; }
    if (error) { return <p className="error-message">{error}</p>; }
    
    // Se não está carregando, não deu erro, e TEMOS dados...
    if (data) {
      // Função auxiliar para formatar números como R$ 1.234,56
      const formatCurrency = (value) => {
        const number = parseFloat(value) || 0;
        return number.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
      };

      return (
        <div className="dashboard-stats">
          {/* Card 1 */}
          <div className="stat-card">
            <h3>Total Receitas</h3>
            <span className={data.total_receitas > 0 ? 'lucro' : ''}>{formatCurrency(data.total_receitas)}</span>
          </div>
          {/* Card 2 */}
          <div className="stat-card">
            <h3>Total Gastos</h3>
            <span className={data.total_gastos > 0 ? 'gasto' : ''}>{formatCurrency(data.total_gastos)}</span>
          </div>
          {/* Card 3 */}
          <div className="stat-card">
            <h3>Lucro Líquido</h3>
            <span className={data.lucro_liquido >= 0 ? 'lucro' : 'gasto'}>{formatCurrency(data.lucro_liquido)}</span>
          </div>
          {/* Card 4 (Ocupa a linha inteira) */}
          <div className="gastos-categoria">
            <h3>Gastos por Categoria</h3>
            <ul>
              {data.gastos_por_categoria.length > 0 ? (
                data.gastos_por_categoria.map((item) => (
                  <li key={item.nome_categoria}>
                    <span>{item.nome_categoria}</span>
                    <span className="gasto">{formatCurrency(item.valor_total)}</span>
                  </li>
                ))
              ) : (
                <p>Nenhum gasto registrado neste período.</p>
              )}
            </ul>
          </div>
        </div>
      );
    }
    return null; // Caso 'data' seja nulo por algum motivo
  };

  // --- O JSX Principal (O que é desenhado) ---
  return (
    <div className="dashboard-container">
      {/* 1. A Barra de Navegação Superior */}
      <nav className="dashboard-nav">
        <h1>Meu Painel Financeiro</h1>
        <div>
          <Link to="/settings" className="nav-link">
            Configurações
          </Link>
          <button onClick={logout} className="logout-button">
            Sair
          </button>
        </div>
      </nav>

      {/* 2. O Cabeçalho da Página (com o botão de Ação) */}
      <header className="dashboard-header">
        <h2>Resumo dos Últimos 30 Dias</h2>
        <button onClick={() => setIsModalOpen(true)} className="add-transaction-button">
          + Registrar Transação
        </button>
      </header>

      {/* 3. O Conteúdo Principal (Cards) */}
      <main className="dashboard-content">
        {renderContent()}
      </main>

      {/* 4. O Modal (Renderização Condicional) */}
      {/* O modal só é "montado" na tela SE 'isModalOpen' for 'true' */}
      {isModalOpen && (
        <TransactionModal 
          onClose={() => setIsModalOpen(false)} 
          onSaveSuccess={handleSaveSuccess} 
        />
      )}
    </div>
  );
}
export default Dashboard;