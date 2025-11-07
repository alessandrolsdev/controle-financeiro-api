// Arquivo: frontend/src/pages/Reports/Reports.jsx
// (VERSÃO V4.6 - LENDO E PASSANDO O TEMA)
/*
REATORAÇÃO (Missão V4.6):
1. Importa 'useTheme' para ler o estado atual do tema.
2. Passa o 'theme' (light/dark) para o TrendChart e HorizontalBarChart.
*/

import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from '../../services/api';
import './Reports.css';

import * as XLSX from 'xlsx'; 
import FilterControls from '../../components/FilterControls/FilterControls';
import HorizontalBarChart from '../../components/HorizontalBarChart/HorizontalBarChart';

// 1. IMPORTA O HOOK DE TEMA
import { useTheme } from '../../context/ThemeContext'; 


// --- Componente Filho "TrendChart" (ATUALIZADO) ---
// Adicionando a prop 'theme'
const TrendChart = ({ data, filterType, theme }) => { // <-- NOVO PROP
  // A cor dinâmica será definida pelo JS
  const axisColor = theme === 'dark' ? '#CED4DA' : '#6C757D'; // Light: Cinza Névoa, Dark: Cinza Suporte
  
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
          stroke={axisColor} // <-- USA A COR DINÂMICA
          tickFormatter={formatXAxis} 
        />
        <YAxis 
          stroke={axisColor} // <-- USA A COR DINÂMICA
          tickFormatter={formatYAxis} 
          orientation="right" 
          yAxisId="right"
        />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: 'var(--cor-fundo-card)', 
            borderColor: 'var(--cor-borda)',
            color: 'var(--cor-texto-principal)' // Já dinâmico via CSS
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
  
  // 3. LÊ O TEMA ATUAL
  const { theme } = useTheme(); // <-- NOVO

  // Estados locais (sem mudança)
  const [lineChartData, setLineChartData] = useState([]);
  const [gastosBarData, setGastosBarData] = useState([]);
  const [receitasBarData, setReceitasBarData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 'useEffect' (Busca todos os dados) - Sem mudança na lógica de fetch
  useEffect(() => {
    // ... (restante da lógica de fetchAllReportData - mantida)
    if (!dataInicioStr || !dataFimStr) return;

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
            count: item.total_compras
          }))
          .sort((a, b) => a.valor - b.valor); 
        setGastosBarData(gastosFormatados);

        // --- Processa Gráfico 3 (Barras de Receitas) ---
        const receitasFormatadas = responseDashboard.data.receitas_por_categoria
          .filter(item => parseFloat(item.valor_total) > 0)
          .map(item => ({
            nome: item.nome_categoria,
            valor: parseFloat(item.valor_total),
            count: item.total_compras
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
  }, [dataInicioStr, dataFimStr, filterType]);
  

  // --- Função de Exportação (Sem mudança) ---
  const handleExport = () => { /* ... (código mantido) ... */
    try {
      // 1. Prepara os dados (formatando para o Excel)
      const dadosFormatados = detailedTransactions.map(tx => ({
        "Data e Hora": new Date(tx.data).toLocaleString('pt-BR', {
          dateStyle: 'short', timeStyle: 'short'
        }),
        "Descricao": tx.descricao,
        "Tipo": tx.categoria.tipo,
        "Categoria": tx.categoria.nome,
        "Valor (R$)": parseFloat(tx.valor) * (tx.categoria.tipo === 'Gasto' ? -1 : 1),
        "Detalhes": tx.observacoes || ''
      }));
      
      const gastos = dadosFormatados.filter(tx => tx.Tipo === 'Gasto');
      const receitas = dadosFormatados.filter(tx => tx.Tipo === 'Receita');

      const wsGeral = XLSX.utils.json_to_sheet(dadosFormatados);
      const wsGastos = XLSX.utils.json_to_sheet(gastos);
      const wsReceitas = XLSX.utils.json_to_sheet(receitas);
      
      const wscols = [ 
        { wch: 20 }, { wch: 30 }, { wch: 10 }, { wch: 20 }, { wch: 15 }, { wch: 40 }
      ];
      wsGeral["!cols"] = wscols;
      wsGastos["!cols"] = wscols;
      wsReceitas["!cols"] = wscols;

      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, wsGeral, "Extrato Geral");
      XLSX.utils.book_append_sheet(wb, wsGastos, "Extrato de Gastos");
      XLSX.utils.book_append_sheet(wb, wsReceitas, "Extrato de Receitas");

      const filename = `Relatorio_Detalhado_NOMAD_${dataInicioStr}_ate_${dataFimStr}.xlsx`;
      XLSX.writeFile(wb, filename);

    } catch (exportError) {
      console.error("Erro ao exportar para Excel:", exportError);
      setError("Ocorreu um erro ao gerar o arquivo Excel.");
    }
  };
  

  return (
    <div className="reports-container">
      <header className="reports-header">
        <h2>Relatórios Visuais</h2>
        {/* Botão de Exportar */}
        {!loading && !error && (gastosBarData.length > 0 || receitasBarData.length > 0) && (
          <button className="export-button" onClick={handleExport}>
            Exportar Excel
          </button>
        )}
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
              // 4. PASSA O TEMA PARA O GRÁFICO
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
              // 5. PASSA O TEMA PARA O GRÁFICO
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
              // 6. PASSA O TEMA PARA O GRÁFICO
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