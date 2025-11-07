// Arquivo: frontend/src/pages/Dashboard/Dashboard.jsx
// (VERSÃO V7.2 - CORREÇÃO DO 'Olá, user.sub')

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useOutletContext } from 'react-router-dom';
import api from '../../services/api';
import './Dashboard.css';
import DoughnutChart from '../../components/DoughnutChart/DoughnutChart';
import FilterControls from '../../components/FilterControls/FilterControls';
import { IoPencil } from 'react-icons/io5'; // (Importa o lápis V6.0)

const formatCurrency = (value) => {
  const number = parseFloat(value) || 0;
  return number.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
};

function Dashboard() {
  // 1. O 'user' agora é o PERFIL COMPLETO (V7.1)
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
    handleEditClick
  } = useOutletContext();
  
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [loadingRecent, setLoadingRecent] = useState(true);
  const [periodTransactions, setPeriodTransactions] = useState([]);
  const [loadingPeriod, setLoadingPeriod] = useState(true);

  // --- Efeitos e Funções (Sem mudança) ---
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
                {onEditClick && (
                  <button className="edit-button" onClick={() => onEditClick(tx)}>
                    <IoPencil size={16} />
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      );
    }
    return (
      <div className="recent-transactions">
        <h2>{title}</h2>
        {content}
      </div>
    );
  };

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
        {/* 2. A CORREÇÃO (V7.2)
            Usa 'nome_completo' (se existir) ou 'nome_usuario' (fallback)
        */}
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