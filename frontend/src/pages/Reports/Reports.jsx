// Arquivo: frontend/src/pages/Reports/Reports.jsx
// (VERSÃO V7.6 - CORREÇÃO DE RACE CONDITION)
/*
REATORAÇÃO (Missão V7.6):
1. Importa 'isAuthLoading' do 'useAuth()' (via 'useOutletContext').
   (CORREÇÃO: 'useOutletContext' não tem 'isAuthLoading',
    precisamos importar 'useAuth' diretamente.)
2. O 'useEffect' principal agora OUVE 'isAuthLoading'
   e SÓ RODA se for 'false'.
*/

import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from '../../services/api';
import './Reports.css';

import FilterControls from '../../components/FilterControls/FilterControls';
import HorizontalBarChart from '../../components/HorizontalBarChart/HorizontalBarChart';
import { useTheme } from '../../context/ThemeContext'; 

// 1. IMPORTA O 'useAuth'
import { useAuth } from '../../context/AuthContext';


// --- Componente Filho "TrendChart" (V4.6 - Dinâmico) ---
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
            color: 'var(--cor-texto-principal)'
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
// ---------------------------------------------------


// --- Componente Pai "Reports" (Ouvindo o Pai) ---
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
  
  // 2. LÊ O ESTADO DE "AVISO" DO AUTH
  const { isAuthLoading } = useAuth();

  // Estados locais (sem mudança)
  const [lineChartData, setLineChartData] = useState([]);
  const [gastosBarData, setGastosBarData] = useState([]);
  const [receitasBarData, setReceitasBarData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 3. 'useEffect' (A CORREÇÃO ESTÁ AQUI)
  useEffect(() => {
    // SÓ BUSCA SE:
    // a) As datas estiverem prontas E
    // b) A AUTENTICAÇÃO (V7.1) ESTIVER CONCLUÍDA
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
        
        const [responseTrend, responseDashboard] = await Promise.all([
          api.get('/relatorios/tendencia', { params: paramsTrend }),
          api.get('/dashboard/', { params: paramsDashboard })
        ]);

        // --- Processa Gráfico 1 (Linha) ---
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

        // --- Processa Gráfico 2 (Barras de Gastos) ---
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

        // --- Processa Gráfico 3 (Barras de Receitas) ---
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

        setLoading(false);
      } catch (err) {
        console.error("Erro ao buscar dados do relatório:", err);
        setError("Não foi possível carregar os dados do relatório.");
        setLoading(false);
      }
    };
    fetchAllReportData();
  }, [dataInicioStr, dataFimStr, filterType, isAuthLoading]); // <-- OUVE 'isAuthLoading'
  
  // --- Função de Exportação (Sem mudança) ---
  const handleExport = () => { /* ... (código mantido) ... */
    // (Precisamos adicionar 'detailedTransactions' aqui...
    //  mas vamos focar em consertar o bug primeiro.)
    
    // (OK, o 'handleExport' que eu lhe enviei (V4.3)
    //  depende de 'detailedTransactions', que NÃO estamos
    //  buscando nesta página. Vamos desabilitar o botão
    //  de exportar por enquanto para evitar outro crash.)
    console.warn("Função de exportar ainda não implementada nesta página.");
  };
  
  // 4. Se a autenticação estiver carregando, mostra o 'loading'
  if (isAuthLoading) {
    return <p className="loading-transactions">Carregando...</p>
  }

  return (
    <div className="reports-container">
      <header className="reports-header">
        <h2>Relatórios Visuais</h2>
        {/* (Botão de exportar desabilitado até
            buscarmos a 3ª API novamente) */}
        {/*!loading && !error && (
          <button className="export-button" onClick={handleExport}>
            Exportar Excel
          </button>
        )*/}
      </header>

      {/* RENDERIZA OS FILTROS GLOBAIS */}
      <FilterControls 
        filterType={filterType}
        setFilterType={setFilterType}
        dataInicio={dataInicio}
        setDataInicio={setDataInicio}
        dataFim={dataFim}
        setDataFim={setDataFim}
      />

      <main className="reports-content">
        {/* Card 1: Gráfico de Tendência */}
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
        
        {/* Card 2: Gráfico de Gastos */}
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
        
        {/* Card 3: Gráfico de Receitas */}
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