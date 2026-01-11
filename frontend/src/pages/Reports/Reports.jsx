// Arquivo: frontend/src/pages/Reports/Reports.jsx
/**
 * @file Página de Relatórios e Análise Financeira.
 * @description Exibe gráficos de tendências, distribuição de receitas/despesas.
 */

import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from '../../services/api';
import './Reports.css';

import FilterControls from '../../components/FilterControls/FilterControls';
import HorizontalBarChart from '../../components/HorizontalBarChart/HorizontalBarChart';

import { useTheme } from '../../context/ThemeContext'; 
import { useAuth } from '../../context/AuthContext';

// REMOVIDO: import * as XLSX from 'xlsx'; (Correção de Segurança/Build)

/**
 * Componente local para renderizar o gráfico de linhas de tendência financeira.
 */
const TrendChart = ({ data, filterType, theme }) => {
  
  const axisColor = theme === 'dark' ? '#CED4DA' : '#6C757D';
  
  const formatXAxis = (tickItem) => {
    const date = new Date(tickItem);
    if (filterType === 'daily') {
      return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
  };
  
  const formatYAxis = (tickItem) => {
    if (tickItem > 1000) {
      return `R$ ${(tickItem / 1000).toLocaleString('pt-BR')}k`;
    }
    return `R$ ${tickItem}`;
  };

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--cor-borda)" />
        <XAxis 
          dataKey="data" 
          stroke={axisColor}
          tickFormatter={formatXAxis} 
        />
        <YAxis 
          stroke={axisColor}
          tickFormatter={formatYAxis} 
          orientation="right" 
          yAxisId="right"
        />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: 'var(--cor-fundo-card)', 
            borderColor: 'var(--cor-borda)',
            color: 'var(--cor-texto-primario)'
          }}
          labelFormatter={(label) => {
            const date = new Date(label);
            if (filterType === 'daily') {
              const offset = date.getTimezoneOffset() * 60000;
              const localDate = new Date(date.valueOf() + offset);
              return localDate.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
            }
            return new Date(label).toLocaleDateString('pt-BR');
          }}
          formatter={(value, name) => [
            value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }), 
            name
          ]}
        />
        <Legend />
        <Line yAxisId="right" type="monotone" dataKey="Receitas" stroke="var(--cor-verde-esmeralda)" strokeWidth={3} dot={false} activeDot={{ r: 8 }} />
        <Line yAxisId="right" type="monotone" dataKey="Despesas" stroke="var(--cor-laranja-voo)" strokeWidth={3} dot={false} activeDot={{ r: 8 }} />
      </LineChart>
    </ResponsiveContainer>
  );
};


function Reports() {
  
  const { 
    dataInicioStr, 
    dataFimStr,
    filterType,
    setFilterType,
    dataInicio,
    setDataInicio,
    dataFim,
    setDataFim
  } = useOutletContext();
  
  const { theme } = useTheme(); 
  const { isAuthLoading } = useAuth();

  const [lineChartData, setLineChartData] = useState([]);
  const [gastosBarData, setGastosBarData] = useState([]);
  const [receitasBarData, setReceitasBarData] = useState([]);
  // const [detailedTransactions, setDetailedTransactions] = useState([]); // Desnecessário sem exportação por enquanto
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!dataInicioStr || !dataFimStr || isAuthLoading) return;

    const fetchAllReportData = async () => {
      setLoading(true);
      setError('');
      
      try {
        const paramsTrend = {
          data_inicio: dataInicioStr,
          data_fim: dataFimStr,
          filtro: filterType
        };
        const paramsDashboard = {
          data_inicio: dataInicioStr,
          data_fim: dataFimStr,
        };
        
        // Removi a chamada de transações detalhadas para otimizar, já que não vamos exportar agora
        const [responseTrend, responseDashboard] = await Promise.all([
          api.get('/relatorios/tendencia', { params: paramsTrend }),
          api.get('/dashboard/', { params: paramsDashboard }),
        ]);

        // Processa dados de Tendência
        const combinedData = {};
        responseTrend.data.receitas.forEach(item => {
          combinedData[item.data] = { ...combinedData[item.data], data: item.data, Receitas: parseFloat(item.valor) };
        });
        responseTrend.data.despesas.forEach(item => {
          combinedData[item.data] = { ...combinedData[item.data], data: item.data, Despesas: parseFloat(item.valor) };
        });
        const finalData = Object.values(combinedData).map(item => ({
          data: item.data,
          Receitas: item.Receitas || 0,
          Despesas: item.Despesas || 0,
        })).sort((a, b) => new Date(a.data) - new Date(b.data));
        setLineChartData(finalData);

        // Processa dados de Gastos por Categoria
        const gastosFormatados = responseDashboard.data.gastos_por_categoria
          .filter(item => parseFloat(item.valor_total) > 0)
          .map(item => ({
            nome: item.nome_categoria,
            valor: parseFloat(item.valor_total),
            count: item.total_compras,
            cor: item.cor
          }))
          .sort((a, b) => a.valor - b.valor);
        setGastosBarData(gastosFormatados);

        // Processa dados de Receitas por Categoria
        const receitasFormatadas = responseDashboard.data.receitas_por_categoria
          .filter(item => parseFloat(item.valor_total) > 0)
          .map(item => ({
            nome: item.nome_categoria,
            valor: parseFloat(item.valor_total),
            count: item.total_compras,
            cor: item.cor
          }))
          .sort((a, b) => a.valor - b.valor);
        setReceitasBarData(receitasFormatadas);

        // setDetailedTransactions(responseTransactions.data); 

        setLoading(false);
        
      } catch (err) {
        console.error("Erro ao buscar dados do relatório:", err);
        setError("Não foi possível carregar os dados do relatório.");
        setLoading(false);
      }
    };

    fetchAllReportData();
  }, [dataInicioStr, dataFimStr, filterType, isAuthLoading]);
  
  
  if (isAuthLoading) {
    return <p className="loading-transactions">Carregando...</p>
  }

  return (
    <div className="reports-container">
      <header className="reports-header">
        <h2>Relatórios Visuais</h2>
        {/* BOTÃO REMOVIDO TEMPORARIAMENTE */}
      </header>

      <FilterControls 
        filterType={filterType}
        setFilterType={setFilterType}
        dataInicio={dataInicio}
        setDataInicio={setDataInicio}
        dataFim={dataFim}
        setDataFim={setDataFim}
      />

      <main className="reports-content">

        <div className="report-card">
          <h3>Saldo ao Longo do Tempo</h3>
          {loading && <p className="loading-transactions">Carregando gráfico...</p>}
          {error && <p className="error-message">Não foi possível carregar os dados do relatório.</p>}
          {!loading && !error && (
            lineChartData.length > 0 ? (
              <TrendChart data={lineChartData} filterType={filterType} theme={theme} /> 
            ) : (
              <p className="loading-transactions">Sem dados de tendência para exibir.</p>
            )
          )}
        </div>
        
        <div className="report-card">
          <h3>Gastos por Categoria - Detalhado</h3>
          {loading && <p className="loading-transactions">Carregando gráfico...</p>}
          {error && <p className="error-message">Não foi possível carregar os dados do relatório.</p>}
          {!loading && !error && (
            gastosBarData.length > 0 ? (
              <HorizontalBarChart data={gastosBarData} theme={theme} />
            ) : (
              <p className="loading-transactions">Sem dados de gastos para exibir.</p>
            )
          )}
        </div>
        
        <div className="report-card">
          <h3>Receitas por Categoria - Detalhado</h3>
          {loading && <p className="loading-transactions">Carregando gráfico...</p>}
          {error && <p className="error-message">Não foi possível carregar os dados do relatório.</p>}
          {!loading && !error && (
            receitasBarData.length > 0 ? (
              <HorizontalBarChart data={receitasBarData} theme={theme} />
            ) : (
              <p className="loading-transactions">Sem dados de receitas para exibir.</p>
            )
          )}
        </div>
      </main>
    </div>
  );
}

export default Reports;