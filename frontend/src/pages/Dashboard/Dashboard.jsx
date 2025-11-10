// Arquivo: frontend/src/pages/Dashboard/Dashboard.jsx
/*
 * Página Principal do Dashboard (O "Hub" de Visualização).
 *
 * Este é o componente principal da aplicação (a rota 'index' /).
 * Ele é um "Filho" do 'MainLayout' e recebe a maior parte de
 * seus dados e estado (filtros, dados de resumo)
 * através do 'useOutletContext()'.
 *
 * Responsabilidades:
 * 1. Renderizar os Filtros Globais (<FilterControls />).
 * 2. Renderizar os Cards de Resumo (Receita, Gasto, Lucro).
 * 3. Renderizar os Gráficos de Rosca (<DoughnutChart />).
 * 4. Buscar e Renderizar as listas de transações:
 * - "Transações no Período" (filtrada)
 * - "Últimas 5 Transações" (não filtrada)
 * 5. Implementar a lógica de Edição (V6.0) e Exclusão (V9.0)
 * para os itens da lista.
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useOutletContext } from 'react-router-dom';
import api from '../../services/api';
import './Dashboard.css';

// Componentes de UI importados
import DoughnutChart from '../../components/DoughnutChart/DoughnutChart';
import FilterControls from '../../components/FilterControls/FilterControls';
import { IoPencil, IoTrash } from 'react-icons/io5'; // Ícones de Ação (V6.0, V9.0)

// --- Função Auxiliar (Helper) ---
/**
 * Formata um valor numérico para a moeda BRL (ex: R$ 5.500,00).
 */
const formatCurrency = (value) => {
  const number = parseFloat(value) || 0;
  return number.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
};


function Dashboard() {
  // 1. CONSUMINDO OS "CÉREBROS" GLOBAIS
  
  // Pega o objeto 'user' (para o "Olá, Alessandro!") (V7.1)
  const { user } = useAuth(); 
  
  // Pega todos os dados e funções injetados pelo 'MainLayout' (Pai)
  const { 
    data, // Os dados do resumo (R$, Gastos) vindos do 'GET /dashboard/'
    loading, // O estado de 'loading' do Pai
    error, // O estado de 'error' do Pai
    filterType,
    setFilterType,
    dataInicio,
    setDataInicio,
    dataFim,
    setDataFim,
    dataInicioStr, // A string de data (AAAA-MM-DD) para a API
    dataFimStr,    // A string de data (AAAA-MM-DD) para a API
    handleEditClick,     // (V6.0) Função do Pai para abrir o modal em modo de edição
    handleDeleteSuccess  // (V9.0) Função do Pai para atualizar o resumo após deletar
  } = useOutletContext();
  
  // --- Estados Locais do Dashboard ---
  // (Este componente gerencia suas próprias listas de transações)
  
  // Lista 1: As 5 últimas (ignora o filtro)
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [loadingRecent, setLoadingRecent] = useState(true);
  
  // Lista 2: Transações filtradas (baseadas no filtro global)
  const [periodTransactions, setPeriodTransactions] = useState([]);
  const [loadingPeriod, setLoadingPeriod] = useState(true);
  
  // Estado para feedback de erro ao deletar
  const [deleteError, setDeleteError] = useState('');

  
  // --- Efeito 1: Busca "Últimas Transações" ---
  // Dispara UMA VEZ quando os dados do Pai (resumo) carregam.
  useEffect(() => {
    // Não busca se o Pai (MainLayout) ainda não carregou os dados
    if (!data) return; 

    setLoadingRecent(true);
    // Chama o endpoint de paginação (ignora filtros de data)
    api.get('/transacoes/?skip=0&limit=5')
      .then(response => {
        setRecentTransactions(response.data);
        setLoadingRecent(false);
      })
      .catch(err => {
        console.error("Erro ao buscar transações recentes:", err);
        setLoadingRecent(false);
      });
  }, [data]); // <-- Gatilho: 'data' (do Pai)

  
  // --- EFEITO 2: Busca "Transações no Período" ---
  // Dispara toda vez que as datas do filtro global (do Pai) mudam.
  // (V9.1 Corrigido: usa 'dataInicioStr' e 'dataFimStr' do Pai)
  useEffect(() => {
    // Não busca se as strings de data ainda não foram calculadas pelo Pai
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
    
  }, [dataInicioStr, dataFimStr]); // <-- Gatilho: as datas do Pai


  // --- Funções "Getters" para os Gráficos ---
  // (Preparam os dados para os componentes <DoughnutChart>)

  // (V5.3 Corrigido: Passa o campo 'cor' para o gráfico)
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
  
  // (V5.3 Corrigido: Passa o campo 'cor' para o gráfico)
  const getReceitasChartData = () => {
      if (data && data.receitas_por_categoria && data.receitas_por_categoria.length > 0) {
        // (V5.0) Usa os dados reais do backend
        return data.receitas_por_categoria
          .filter(item => parseFloat(item.valor_total) > 0)
          .map(item => ({
            nome: item.nome_categoria,
            valor: parseFloat(item.valor_total),
            count: item.total_compras,
            cor: item.cor
          }));
      }
      // (Fallback se não houver receitas, mas houver valor total)
      if (data && data.total_receitas > 0) {
          const totalReceitasFloat = parseFloat(data.total_receitas);
          return [
            { nome: 'Serviços', valor: totalReceitasFloat, count: 1, cor: '#00E08F' }, // Mock com cor
          ].filter(item => item.valor > 0);
      }
      return [];
  };
  
  // (V3.8) Gera o subtítulo dinâmico (ex: "Resumo de quinta-feira...")
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
  
  // --- Lógica de CRUD (Exclusão V9.0) ---
  /**
   * Chamado ao clicar no ícone de lixeira (Delete).
   * Chama o endpoint SÍNCRONO de delete.
   */
  const handleDeleteTransaction = async (transaction) => {
    setDeleteError(''); // Limpa erros antigos
    
    if (!window.confirm(`Tem certeza que deseja excluir a transação: "${transaction.descricao}"?`)) {
      return;
    }
    
    try {
      // Chama o endpoint SÍNCRONO (V-Revert)
      // (Envia as datas do filtro para o backend recalcular)
      const response = await api.delete(`/transacoes/${transaction.id}`, {
        params: {
          data_inicio: dataInicioStr,
          data_fim: dataFimStr
        }
      });
      
      // A 'response.data' é o DashboardData atualizado
      // Passa os dados para o Pai (MainLayout) atualizar o estado
      handleDeleteSuccess(response.data);
      
    } catch (err) {
      console.error("Erro ao deletar transação:", err);
      setDeleteError("Não foi possível excluir a transação. Tente novamente.");
    }
  };
  
  
  /**
   * Função auxiliar para renderizar UMA lista de transações (V2.11)
   * (Usada 2x: "Período" e "Últimas 5")
   * @param {boolean} showActions - Se deve renderizar os botões de Editar/Deletar
   */
  const renderTransactionList = (title, transactions, loadingState, showActions) => {
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
              {/* Lado Esquerdo: Detalhes */}
              <div className="transaction-details">
                <span>{tx.descricao}</span>
                <span className="transaction-date">
                  {new Date(tx.data).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
                  , {new Date(tx.data).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              
              {/* Lado Direito: Ações e Valor */}
              <div className="transaction-actions">
                <span className={`transaction-amount ${tx.categoria.tipo === 'Gasto' ? 'gasto' : 'lucro'}`}>
                  {tx.categoria.tipo === 'Gasto' ? '-' : '+'}
                  {formatCurrency(tx.valor)}
                </span>
                
                {/* (V6.0 / V9.0) Mostra os botões de Ação */}
                {showActions && (
                  <>
                    <button className="edit-button" onClick={() => handleEditClick(tx)}>
                      <IoPencil size={16} />
                    </button>
                    <button className="delete-button" onClick={() => handleDeleteTransaction(tx)}>
                      <IoTrash size={16} />
                    </button>
                  </>
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
        {/* Mostra o erro de 'delete' (se houver) apenas no card "Período" */}
        {title === "Transações no Período" && deleteError && 
          <p className="error-message">{deleteError}</p>}
        {content}
      </div>
    );
  };

  /**
   * Renderiza o conteúdo principal (Cards, Gráficos, Listas)
   * (Só é chamado se 'loading' (do Pai) for false)
   */
  const renderContent = () => {
    // Se o Pai (MainLayout) estiver carregando ou falhar, mostra o status.
    if (loading) { return <p className="dashboard-loading">Carregando dados...</p>; }
    if (error) { return <p className="error-message">{error}</p>; }
    
    // Se os dados do Pai (resumo) estiverem prontos
    if (data) {
      const gastosChartData = getGastosChartData();
      const receitasChartData = getReceitasChartData();
      
      return (
        <>
          {/* 1. Cards de Resumo */}
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
          
          {/* 2. Gráficos de Rosca */}
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

          {/* 3. Listas de Transações */}
          {renderTransactionList(
            "Transações no Período", 
            periodTransactions, 
            loadingPeriod,
            true // <-- Sim, mostrar botões de ação
          )}
          {renderTransactionList(
            "Últimas 5 Transações", 
            recentTransactions, 
            loadingRecent,
            true // <-- Sim, mostrar botões de ação
          )}
        </>
      );
    }
    return null;
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        {/* (V7.2) "Olá, [Nome Completo]" ou "Olá, [nome_usuario]" */}
        <h2>Olá, {user ? (user.nome_completo || user.nome_usuario) : '...'}!</h2>
        <span className="dashboard-subtitle">{getSubtituloFiltro()}</span>
      </header>

      {/* A UI DO FILTRO (Componente V3.3) */}
      <FilterControls 
        filterType={filterType}
        setFilterType={setFilterType}
        dataInicio={dataInicio}
        setDataInicio={setDataInicio}
        dataFim={dataFim}
        setDataFim={setDataFim}
      />

      {/* O Conteúdo Principal (Cards, Gráficos, Listas) */}
      <main className="dashboard-content">
        {renderContent()}
      </main>
    </div>
  );
}

export default Dashboard;