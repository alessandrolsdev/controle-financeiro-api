// Arquivo: frontend/src/pages/Reports/Reports.jsx
/*
 * Página de Relatórios Visuais.
 *
 * Este componente é um "Filho" do 'MainLayout' (assim como o Dashboard).
 * Sua responsabilidade é consumir o filtro de data global e
 * exibir visualizações de dados detalhadas.
 *
 * Responsabilidades:
 * 1. Renderizar os Filtros Globais (<FilterControls />).
 * 2. Buscar dados de 3 endpoints da API em paralelo
 * (Tendência, Resumo do Dashboard, Lista Detalhada).
 * 3. Renderizar o gráfico de Linha (TrendChart).
 * 4. Renderizar os gráficos de Barra (Gastos e Receitas).
 * 5. Implementar a lógica de 'Exportar para Excel' (V4.3).
 * 6. Passar o 'theme' (Light/Dark) para os gráficos para
 * corrigir o contraste do SVG (V4.6).
 */

import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from '../../services/api';
import './Reports.css';

// Importa a biblioteca de Excel (V4.2)
import * as XLSX from 'xlsx'; 

// Importa os componentes de UI
import FilterControls from '../../components/FilterControls/FilterControls';
import HorizontalBarChart from '../../components/HorizontalBarChart/HorizontalBarChart';

// Importa os "cérebros" de contexto
import { useTheme } from '../../context/ThemeContext'; 
import { useAuth } from '../../context/AuthContext';


// --- Componente Filho "TrendChart" (Gráfico de Linha V4.6) ---
// (Definido localmente, pois é usado apenas aqui)

/**
 * Renderiza o gráfico de linha "Saldo ao Longo do Tempo".
 *
 * @param {object} props
 * @param {Array<object>} props.data - Os dados formatados.
 * @param {string} props.filterType - 'daily', 'monthly', etc. (para formatar o eixo X).
 * @param {string} props.theme - 'light' ou 'dark' (para a cor dos eixos).
 */
const TrendChart = ({ data, filterType, theme }) => {
  
  // Decisão de Engenharia (V4.6):
  // O SVG (recharts) não lê variáveis CSS.
  // Definimos a cor do texto do eixo (stroke) via JavaScript.
  const axisColor = theme === 'dark' ? '#CED4DA' : '#6C757D'; // Dark: Cinza Suporte, Light: Cinza Névoa
  
  /**
   * Formata o eixo X (horizontal)
   * Se for 'daily', mostra "14:00".
   * Se não, mostra "06/Nov".
   */
  const formatXAxis = (tickItem) => {
    const date = new Date(tickItem);
    if (filterType === 'daily') {
      return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
  };
  
  /** Formata o eixo Y (vertical) (ex: "R$ 10k") */
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
        {/* Decisão de Design (V3.0): Eixo Y movido para a direita. */}
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
              // (V3.7) Corrige o fuso horário do tooltip para 'daily'
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


// --- Componente Pai "Reports" ---
function Reports() {
  
  // 1. CONSUMINDO OS "CÉREBROS" GLOBAIS
  
  // Pega todos os dados e funções do filtro global (do MainLayout)
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
  
  // Pega o tema (light/dark) para passar aos gráficos
  const { theme } = useTheme(); 
  // Pega o status de loading da autenticação (para evitar race conditions)
  const { isAuthLoading } = useAuth();

  // --- Estados Locais (para os dados dos 3 gráficos) ---
  const [lineChartData, setLineChartData] = useState([]);
  const [gastosBarData, setGastosBarData] = useState([]);
  const [receitasBarData, setReceitasBarData] = useState([]);
  const [detailedTransactions, setDetailedTransactions] = useState([]); // (Para o Excel)
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  
  /**
   * Efeito Principal: Busca TODOS os dados dos relatórios.
   *
   * Dispara quando os filtros (do Pai) mudam, mas ESPERA
   * a autenticação ('isAuthLoading') estar pronta.
   */
  useEffect(() => {
    // V7.6: Espera o AuthContext e os filtros estarem prontos
    if (!dataInicioStr || !dataFimStr || isAuthLoading) return;

    const fetchAllReportData = async () => {
      setLoading(true);
      setError('');
      
      try {
        // Prepara os parâmetros para as 3 chamadas de API
        const paramsTrend = {
          data_inicio: dataInicioStr,
          data_fim: dataFimStr,
          filtro: filterType // (Envia 'daily', 'monthly', etc. - V3.7)
        };
        const paramsDashboard = {
          data_inicio: dataInicioStr,
          data_fim: dataFimStr,
        };
        
        // V9.5: Busca as 3 fontes de dados em paralelo
        const [responseTrend, responseDashboard, responseTransactions] = await Promise.all([
          api.get('/relatorios/tendencia', { params: paramsTrend }), // Gráfico 1
          api.get('/dashboard/', { params: paramsDashboard }),       // Gráfico 2 e 3
          api.get('/transacoes/periodo/', { params: paramsDashboard }) // Para o Excel
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
            cor: item.cor // (V5.0) Passa a cor dinâmica
          }))
          .sort((a, b) => a.valor - b.valor); // (Ordena menor -> maior)
        setGastosBarData(gastosFormatados);

        // --- Processa Gráfico 3 (Barras de Receitas) ---
        const receitasFormatadas = responseDashboard.data.receitas_por_categoria
          .filter(item => parseFloat(item.valor_total) > 0)
          .map(item => ({
            nome: item.nome_categoria,
            valor: parseFloat(item.valor_total),
            count: item.total_compras,
            cor: item.cor // (V5.0) Passa a cor dinâmica
          }))
          .sort((a, b) => a.valor - b.valor);
        setReceitasBarData(receitasFormatadas);

        // --- Salva a Lista Detalhada (para o Excel) ---
        setDetailedTransactions(responseTransactions.data); 

        setLoading(false);
        
      } catch (err) {
        console.error("Erro ao buscar dados do relatório:", err);
        setError("Não foi possível carregar os dados do relatório.");
        setLoading(false);
      }
    };

    fetchAllReportData();
  }, [dataInicioStr, dataFimStr, filterType, isAuthLoading]); // <-- Ouve todos os gatilhos
  
  
  /**
   * Função de Exportação para Excel (V4.3).
   * Usa a lista 'detailedTransactions' (do estado)
   * para gerar um arquivo .xlsx detalhado com 3 abas.
   */
  const handleExport = () => {
    try {
      if (detailedTransactions.length === 0) {
        alert("Não há transações para exportar neste período.");
        return;
      }

      // 1. Formata os dados (como você pediu: Detalhes, Data, Categoria, etc.)
      const dadosFormatados = detailedTransactions.map(tx => ({
        "Data e Hora": new Date(tx.data).toLocaleString('pt-BR', {
          dateStyle: 'short', timeStyle: 'short'
        }),
        "Descricao": tx.descricao,
        "Tipo": tx.categoria.tipo,
        "Categoria": tx.categoria.nome,
        // (V4.3) Formata o valor (positivo/negativo)
        "Valor (R$)": parseFloat(tx.valor) * (tx.categoria.tipo === 'Gasto' ? -1 : 1),
        "Detalhes": tx.observacoes || ''
      }));
      
      // 2. Filtra para abas separadas
      const gastos = dadosFormatados.filter(tx => tx.Tipo === 'Gasto');
      const receitas = dadosFormatados.filter(tx => tx.Tipo === 'Receita');

      // 3. Cria as Planilhas (Worksheets)
      const wsGeral = XLSX.utils.json_to_sheet(dadosFormatados);
      const wsGastos = XLSX.utils.json_to_sheet(gastos);
      const wsReceitas = XLSX.utils.json_to_sheet(receitas);
      
      // Define a largura das colunas
      const wscols = [ 
        { wch: 20 }, { wch: 30 }, { wch: 10 }, { wch: 20 }, { wch: 15 }, { wch: 40 }
      ];
      wsGeral["!cols"] = wscols;
      wsGastos["!cols"] = wscols;
      wsReceitas["!cols"] = wscols;

      // 4. Cria o "Arquivo" (Workbook) e adiciona as abas
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, wsGeral, "Extrato Geral");
      XLSX.utils.book_append_sheet(wb, wsGastos, "Extrato de Gastos");
      XLSX.utils.book_append_sheet(wb, wsReceitas, "Extrato de Receitas");

      // 5. Gera o arquivo e força o download
      const filename = `Relatorio_Detalhado_NOMAD_${dataInicioStr}_ate_${dataFimStr}.xlsx`;
      XLSX.writeFile(wb, filename);

    } catch (exportError) {
      console.error("Erro ao exportar para Excel:", exportError);
      setError("Ocorreu um erro ao gerar o arquivo Excel.");
    }
  };
  
  // (V7.6) Tela de carregamento global
  if (isAuthLoading) {
    return <p className="loading-transactions">Carregando...</p>
  }

  return (
    <div className="reports-container">
      <header className="reports-header">
        <h2>Relatórios Visuais</h2>
        {/* (V9.6) O botão aparece se os dados estiverem prontos */}
        {!loading && !error && (
          <button 
            className={`export-button ${detailedTransactions.length === 0 ? 'export-button-disabled' : ''}`}
            onClick={handleExport}
            disabled={detailedTransactions.length === 0}
          >
            {detailedTransactions.length === 0 ? 'Exportar Excel (sem dados)' : 'Exportar Excel'}
          </button>
        )}
      </header>

      {/* RENDERIZA OS FILTROS GLOBAIS (V3.3) */}
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
              // (V4.6) Passa o 'theme' e 'filterType'
              <TrendChart data={lineChartData} filterType={filterType} theme={theme} /> 
            ) : (
              <p className="loading-transactions">Sem dados de tendência para exibir.</p>
            )
          )}
        </div>
        
        {/* Card 2: Gráfico de Gastos (V3.4) */}
        <div className="report-card">
          <h3>Gastos por Categoria - Detalhado</h3>
          {loading && <p className="loading-transactions">Carregando gráfico...</p>}
          {error && <p className="error-message">Não foi possível carregar os dados do relatório.</p>}
          {!loading && !error && (
            gastosBarData.length > 0 ? (
              // (V4.6) Passa o 'theme'
              <HorizontalBarChart data={gastosBarData} theme={theme} />
            ) : (
              <p className="loading-transactions">Sem dados de gastos para exibir.</p>
            )
          )}
        </div>
        
        {/* Card 3: Gráfico de Receitas (V3.4) */}
        <div className="report-card">
          <h3>Receitas por Categoria - Detalhado</h3>
          {loading && <p className="loading-transactions">Carregando gráfico...</p>}
          {error && <p className="error-message">Não foi possível carregar os dados do relatório.</p>}
          {!loading && !error && (
            receitasBarData.length > 0 ? (
              // (V4.6) Passa o 'theme'
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