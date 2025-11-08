// Arquivo: frontend/src/pages/Dashboard/Dashboard.jsx
// (VERSÃO V9.0 - COM BOTÃO DE EXCLUIR)
/*
REATORAÇÃO (Missão V9.0):
1. Importa 'IoTrash' (Lixeira).
2. Recebe 'handleDeleteSuccess' do Pai (via 'useOutletContext').
3. Adiciona a nova função local 'handleDeleteTransaction'.
4. 'handleDeleteTransaction' chama o novo endpoint 'api.delete'
   e passa os dados atualizados para 'handleDeleteSuccess'.
5. 'renderTransactionList' agora renderiza o botão de lixeira.
*/

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useOutletContext } from 'react-router-dom';
import api from '../../services/api';
import './Dashboard.css';
import DoughnutChart from '../../components/DoughnutChart/DoughnutChart';
import FilterControls from '../../components/FilterControls/FilterControls';

// 1. IMPORTA O ÍCONE DE LIXEIRA
import { IoPencil, IoTrash } from 'react-icons/io5';

// --- (Função Auxiliar) ---
const formatCurrency = (value) => {
  const number = parseFloat(value) || 0;
  return number.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
};

function Dashboard() {
  const { user } = useAuth(); 
  
  // 2. RECEBE O NOVO HANDLER DO PAI
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
    handleDeleteSuccess // <-- NOVO HANDLER
  } = useOutletContext();
  
  // --- Estados Locais (Sem mudança) ---
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [loadingRecent, setLoadingRecent] = useState(true);
  const [periodTransactions, setPeriodTransactions] = useState([]);
  const [loadingPeriod, setLoadingPeriod] = useState(true);
  
  // (Este estado é para o feedback do 'delete')
  const [deleteError, setDeleteError] = useState('');

  // --- Efeito 1: Busca "Últimas Transações" ---
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

  // --- EFEITO 2: Busca "Transações no Período" ---
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

  // --- Funções Auxiliares (getGastosChartData, etc. - Sem mudança) ---
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
  
  // 3. A NOVA FUNÇÃO DE DELETAR (V9.0)
  const handleDeleteTransaction = async (transaction) => {
    setDeleteError(''); // Limpa erros antigos
    
    if (!window.confirm(`Tem certeza que deseja excluir a transação: "${transaction.descricao}"?`)) {
      return;
    }
    
    try {
      // Chama o endpoint SÍNCRONO de 'delete'
      // (Envia as datas do filtro para o backend recalcular)
      const response = await api.delete(`/transacoes/${transaction.id}`, {
        params: {
          data_inicio: dataInicioStr,
          data_fim: dataFimStr
        }
      });
      
      // A 'response.data' é o DashboardData atualizado
      handleDeleteSuccess(response.data);
      
    } catch (err) {
      console.error("Erro ao deletar transação:", err);
      // (Não usamos 'alert' aqui para não ser muito intrusivo)
      setDeleteError("Não foi possível excluir a transação. Tente novamente.");
    }
  };
  
  
  // 4. FUNÇÃO DE RENDERIZAR LISTAS (ATUALIZADA)
  const renderTransactionList = (title, transactions, loadingState, onEditClick) => {
    let content;
    if (loadingState) {
      content = <p className="loading-transactions">Buscando transações...</p>;
    } else if (transactions.length === 0) {
      content = <p className="loading-transactions">Nenhuma transação encontrada.</p>;
    } else {
      content = (
        <ul>
          {transactions.map((tx) => (
            <li key={tx.id}>
              <div className="transaction-details">
                <span>{tx.descricao}</span>
                <span className="transaction-date">
                  {new Date(tx.data).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
                  , {new Date(tx.data).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              
              <div className="transaction-actions">
                <span className={`transaction-amount ${tx.categoria.tipo === 'Gasto' ? 'gasto' : 'lucro'}`}>
                  {tx.categoria.tipo === 'Gasto' ? '-' : '+'}
                  {formatCurrency(tx.valor)}
                </span>
                
                {/* Botão de Editar (V6.0) */}
                {onEditClick && (
                  <button className="edit-button" onClick={() => onEditClick(tx)}>
                    <IoPencil size={16} />
                  </button>
                )}
                
                {/* 5. O NOVO BOTÃO DE EXCLUIR (V9.0) */}
                <button className="delete-button" onClick={() => handleDeleteTransaction(tx)}>
                  <IoTrash size={16} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      );
    }
    return (
      <div className="recent-transactions">
        <h2>{title}</h2>
        {/* Mostra o erro de 'delete' (se houver) */}
        {title === "Transações no Período" && deleteError && 
          <p className="error-message">{deleteError}</p>}
        {content}
      </div>
    );
  };

  // --- Renderização (Conteúdo Principal) ---
  const renderContent = () => {
    if (loading) { return <p className="dashboard-loading">Carregando dados...</p>; }
    if (error) { return <p className="error-message">{error}</p>; }
    
    if (data) {
      const gastosChartData = getGastosChartData();
      const receitasChartData = getReceitasChartData();
      return (
        <>
          <div className="dashboard-stats">
             <div className="stat-card">
              <h3>Total Receitas</h3>
              <span className="lucro">{formatCurrency(data.total_receitas)}</span>
            </div>
            <div className="stat-card">
              <h3>Total Gastos</h3>
              <span className="gasto">{formatCurrency(data.total_gastos)}</span>
            </div>
            <div className="stat-card">
              <h3>Lucro Líquido</h3>
              <span className={data.lucro_liquido >= 0 ? 'lucro' : 'gasto'}>
                {formatCurrency(data.lucro_liquido)}
              </span>
            </div>
          </div>
          
          <div className="dashboard-charts-grid">
            <div className="chart-container">
              <h3>Receitas por Categoria</h3>
              <DoughnutChart 
                chartData={receitasChartData}
                totalValue={parseFloat(data.total_receitas)}
                centerLabel="Total Receita"
              />
            </div>
            <div className="chart-container">
              <h3>Gastos por Categoria</h3>
              <DoughnutChart 
                chartData={gastosChartData}
                totalValue={parseFloat(data.total_gastos)}
                centerLabel="Total Gasto"
              />
            </div>
          </div>

          {/* (As listas agora têm 'handleEditClick') */}
          {renderTransactionList("Transações no Período", periodTransactions, loadingPeriod, handleEditClick)}
          {renderTransactionList("Últimas 5 Transações", recentTransactions, loadingRecent, handleEditClick)}
        </>
      );
    }
    return null;
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h2>Olá, {user ? (user.nome_completo || user.nome_usuario) : '...'}!</h2>
        <span className="dashboard-subtitle">{getSubtituloFiltro()}</span>
      </header>

      <FilterControls 
        filterType={filterType}
        setFilterType={setFilterType}
        dataInicio={dataInicio}
        setDataInicio={setDataInicio}
        dataFim={dataFim}
        setDataFim={setDataFim}
      />

      <main className="dashboard-content">
        {renderContent()}
      </main>
    </div>
  );
}

export default Dashboard;