// Arquivo: frontend/src/pages/Dashboard/Dashboard.jsx
/**
 * @file Página Dashboard.
 * @description Exibe o resumo financeiro, gráficos de receita/despesa e listas de transações. Permite filtragem por data.
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../../context/useAuth';
import { useOutletContext } from 'react-router-dom';
import api from '../../services/api';
import './Dashboard.css';

import DoughnutChart from '../../components/DoughnutChart/DoughnutChart';
import FilterControls from '../../components/FilterControls/FilterControls';
import { IoPencil, IoTrash } from 'react-icons/io5';

/**
 * Formata um valor numérico para o formato de moeda BRL.
 * @param {number|string} value - O valor a ser formatado.
 * @returns {string} O valor formatado como moeda.
 */
const formatCurrency = (value) => {
  const number = parseFloat(value) || 0;
  return number.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
};

/**
 * Componente Dashboard.
 *
 * Principal interface do usuário. Consome dados globais do MainLayout e exibe:
 * - Filtros de data.
 * - Cards com totais (Receitas, Gastos, Lucro).
 * - Gráficos de rosca detalhando categorias.
 * - Listas de transações recentes e do período selecionado.
 * - Funcionalidades de editar e excluir transações.
 *
 * @returns {JSX.Element} A página do dashboard renderizada.
 */
function Dashboard() {
  
  const { user } = useAuth(); 
  
  const { 
    data,
    loading,
    error,
    filterType,
    setFilterType,
    dataInicio,
    setDataInicio,
    dataFim,
    setDataFim,
    dataInicioStr,
    dataFimStr,
    handleEditClick,
    handleDeleteSuccess
  } = useOutletContext();
  
  // --- Estados Locais ---
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [loadingRecent, setLoadingRecent] = useState(true);
  
  const [periodTransactions, setPeriodTransactions] = useState([]);
  const [loadingPeriod, setLoadingPeriod] = useState(true);
  
  const [deleteError, setDeleteError] = useState('');

  
  /**
   * Efeito colateral para buscar as 5 últimas transações.
   * Executa quando os dados principais (data) são carregados.
   */
  useEffect(() => {
    if (!data) return; 

    setLoadingRecent(true);
    api.get('/transacoes/?skip=0&limit=5')
      .then(response => {
        setRecentTransactions(response.data);
        setLoadingRecent(false);
      })
      .catch(err => {
        console.error("Erro ao buscar transações recentes:", err);
        setLoadingRecent(false);
      });
  }, [data]);

  
  /**
   * Efeito colateral para buscar transações do período filtrado.
   * Executa quando as strings de data (dataInicioStr, dataFimStr) mudam.
   */
  useEffect(() => {
    if (!dataInicioStr || !dataFimStr) return;

    const fetchPeriodTransactions = async () => {
      setLoadingPeriod(true);
      try {
        const response = await api.get('/transacoes/periodo/', {
          params: {
            data_inicio: dataInicioStr,
            data_fim: dataFimStr
          }
        });
        setPeriodTransactions(response.data);
      } catch (err) {
        console.error("Erro ao buscar transações do período:", err);
      }
      setLoadingPeriod(false);
    };
    
    fetchPeriodTransactions();
    
  }, [dataInicioStr, dataFimStr]);

  /**
   * Prepara os dados para o gráfico de gastos.
   */
  const getGastosChartData = () => {
      return data && data.gastos_por_categoria
      ? data.gastos_por_categoria
          .filter(item => parseFloat(item.valor_total) > 0) 
          .map(item => ({
            nome: item.nome_categoria,
            valor: parseFloat(item.valor_total),
            count: item.total_compras,
            cor: item.cor 
          }))
      : []; 
  };
  
  /**
   * Prepara os dados para o gráfico de receitas.
   */
  const getReceitasChartData = () => {
      if (data && data.receitas_por_categoria && data.receitas_por_categoria.length > 0) {
        return data.receitas_por_categoria
          .filter(item => parseFloat(item.valor_total) > 0)
          .map(item => ({
            nome: item.nome_categoria,
            valor: parseFloat(item.valor_total),
            count: item.total_compras,
            cor: item.cor
          }));
      }
      if (data && data.total_receitas > 0) {
          const totalReceitasFloat = parseFloat(data.total_receitas);
          return [
            { nome: 'Serviços', valor: totalReceitasFloat, count: 1, cor: '#00E08F' },
          ].filter(item => item.valor > 0);
      }
      return [];
  };
  
  /**
   * Gera o texto do subtítulo baseado no filtro selecionado.
   */
  const getSubtituloFiltro = () => {
    const dataInicioObj = new Date(dataInicio);
    const dataFimObj = new Date(dataFim);
    switch (filterType) {
      case 'weekly':
        return `Resumo da Semana: ${dataInicioObj.toLocaleDateString('pt-BR')} - ${dataFimObj.toLocaleDateString('pt-BR')}`;
      case 'monthly':
        return `Resumo de: ${dataInicioObj.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })}`;
      case 'yearly':
        return `Resumo do Ano de: ${dataInicioObj.getFullYear()}`;
      case 'personalizado':
         return `Resumo: ${dataInicioObj.toLocaleDateString('pt-BR')} - ${dataFimObj.toLocaleDateString('pt-BR')}`;
      case 'daily':
      default:
        return `Resumo de: ${dataInicioObj.toLocaleDateString('pt-BR', { dateStyle: 'full' })}`;
    }
  };
  
  /**
   * Manipula a exclusão de uma transação.
   * Solicita confirmação e chama a API para deleção, atualizando o dashboard em seguida.
   *
   * @param {object} transaction - A transação a ser excluída.
   */
  const handleDeleteTransaction = async (transaction) => {
    setDeleteError('');
    
    if (!window.confirm(`Tem certeza que deseja excluir a transação: "${transaction.descricao}"?`)) {
      return;
    }
    
    try {
      const response = await api.delete(`/transacoes/${transaction.id}`, {
        params: {
          data_inicio: dataInicioStr,
          data_fim: dataFimStr
        }
      });
      
      handleDeleteSuccess(response.data);
      
    } catch (err) {
      console.error("Erro ao deletar transação:", err);
      setDeleteError("Não foi possível excluir a transação. Tente novamente.");
    }
  };
  
  /**
   * Renderiza uma lista de transações.
   *
   * @param {string} title - O título da seção da lista.
   * @param {Array} transactions - Lista de transações a exibir.
   * @param {boolean} loadingState - Estado de carregamento.
   * @param {boolean} showActions - Se deve exibir botões de editar/excluir.
   * @returns {JSX.Element} O componente da lista.
   */
  const renderTransactionList = (title, transactions, loadingState, showActions) => {
    let content;

    if (loadingState) {
      content = <p className="vazio">Carregando…</p>;
    } else if (transactions.length === 0) {
      content = <p className="vazio">Nenhuma transação neste período.</p>;
    } else {
      content = (
        <ul className="transacoes">
          {transactions.map((tx) => {
            const ehGasto = tx.categoria.tipo === 'Gasto';

            return (
              <li key={tx.id} className="transacao">
                <span
                  className="transacao-marcador"
                  style={{ backgroundColor: tx.categoria.cor }}
                  aria-hidden="true"
                />

                <div className="transacao-info">
                  <span className="transacao-descricao">{tx.descricao}</span>
                  <span className="transacao-meta">
                    {tx.categoria.nome} ·{' '}
                    {new Date(tx.data).toLocaleDateString('pt-BR', {
                      day: '2-digit',
                      month: 'short',
                    })}
                  </span>
                </div>

                <span
                  className={
                    ehGasto ? 'transacao-valor valor-despesa' : 'transacao-valor valor-receita'
                  }
                >
                  {ehGasto ? '−' : '+'}
                  {formatCurrency(tx.valor)}
                </span>

                {showActions && (
                  <div className="transacao-acoes">
                    <button
                      type="button"
                      className="botao-discreto"
                      onClick={() => handleEditClick(tx)}
                      aria-label={`Editar ${tx.descricao}`}
                    >
                      <IoPencil size={15} />
                    </button>
                    <button
                      type="button"
                      className="botao-discreto"
                      onClick={() => handleDeleteTransaction(tx)}
                      aria-label={`Excluir ${tx.descricao}`}
                    >
                      <IoTrash size={15} />
                    </button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      );
    }

    return (
      <section className="painel">
        <div className="painel-cabecalho">
          <h3>{title}</h3>
        </div>
        {deleteError && (
          <div style={{ padding: 'var(--e-4)' }}>
            <p className="mensagem mensagem-erro">{deleteError}</p>
          </div>
        )}
        {content}
      </section>
    );
  };

  /**
   * Renderiza o conteúdo principal do dashboard quando os dados estão carregados.
   */
  const renderContent = () => {
    if (loading) return <p className="vazio">Carregando dados…</p>;
    if (error) return <p className="mensagem mensagem-erro">{error}</p>;
    
    if (data) {
      const gastosChartData = getGastosChartData();
      const receitasChartData = getReceitasChartData();
      
      return (
        <>
          <div className="resumo">
            <div className="resumo-card">
              <span className="resumo-rotulo">Receitas</span>
              <span className="resumo-valor valor-receita">
                {formatCurrency(data.total_receitas)}
              </span>
            </div>
            <div className="resumo-card">
              <span className="resumo-rotulo">Despesas</span>
              <span className="resumo-valor valor-despesa">
                {formatCurrency(data.total_gastos)}
              </span>
            </div>
            <div className="resumo-card">
              <span className="resumo-rotulo">Saldo</span>
              <span
                className={
                  Number(data.lucro_liquido) >= 0
                    ? 'resumo-valor valor-receita'
                    : 'resumo-valor valor-despesa'
                }
              >
                {formatCurrency(data.lucro_liquido)}
              </span>
              <span className="resumo-detalhe">Receitas menos despesas</span>
            </div>
          </div>

          <div className="graficos">
            <section className="painel">
              <div className="painel-cabecalho">
                <h3>Receitas por categoria</h3>
              </div>
              <div className="painel-corpo">
                <DoughnutChart
                  chartData={receitasChartData}
                  totalValue={parseFloat(data.total_receitas)}
                  centerLabel="Receitas"
                />
              </div>
            </section>

            <section className="painel">
              <div className="painel-cabecalho">
                <h3>Despesas por categoria</h3>
              </div>
              <div className="painel-corpo">
                <DoughnutChart
                  chartData={gastosChartData}
                  totalValue={parseFloat(data.total_gastos)}
                  centerLabel="Despesas"
                />
              </div>
            </section>
          </div>

          <div className="graficos">
            {renderTransactionList(
              'Transações no período',
              periodTransactions,
              loadingPeriod,
              true
            )}
            {renderTransactionList(
              'Mais recentes',
              recentTransactions,
              loadingRecent,
              true
            )}
          </div>
        </>
      );
    }
    return null;
  };

  return (
    <>
      <header className="cabecalho-pagina">
        <div>
          <h1>Olá, {user ? user.nome_completo || user.nome_usuario : '…'}</h1>
          <p>{getSubtituloFiltro()}</p>
        </div>
      </header>

      <FilterControls 
        filterType={filterType}
        setFilterType={setFilterType}
        dataInicio={dataInicio}
        setDataInicio={setDataInicio}
        dataFim={dataFim}
        setDataFim={setDataFim}
      />

      {renderContent()}
    </>
  );
}

export default Dashboard;
