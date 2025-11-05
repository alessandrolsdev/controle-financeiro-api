// Arquivo: frontend/src/components/DoughnutChart/DoughnutChart.jsx
// (VERSÃO V3.3 - Tooltip Inteligente)

import React from 'react';
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import './DoughnutChart.css';

ChartJS.register(ArcElement, Tooltip, Legend);

/**
 * @param {object[]} chartData - Array de { nome: string, valor: number, count: number }
 * @param {number} totalValue - O valor total para exibir no centro
 * @param {string} centerLabel - O texto do rótulo central
 */
function DoughnutChart({ chartData, totalValue, centerLabel }) {

  const colorsPalette = [
    '#FF7A00', // Laranja Voo
    '#00E08F', // Verde Esmeralda
    '#D400E6', // Magenta Dinâmico
    '#FFC107', '#20C997', '#6F42C1',
  ];

  const data = {
    labels: chartData.map(c => c.nome),
    datasets: [
      {
        data: chartData.map(c => c.valor),
        backgroundColor: chartData.map((_, i) => colorsPalette[i % colorsPalette.length]),
        borderColor: '#1C2B4A', 
        borderWidth: 3,
      },
    ],
  };

  const formatCurrency = (value) => {
    return (parseFloat(value) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  // --- A CORREÇÃO DA TOOLTIP ESTÁ AQUI ---
  const options = {
    responsive: true,
    maintainAspectRatio: false, 
    cutout: '75%', 
    plugins: {
      legend: { display: false },
      tooltip: {
        // --- 1. Correção do "Pulo" e "Seguir" ---
        // 'nearest' e 'intersect: false' fazem a tooltip
        // aparecer suavemente ao passar perto, sem "pular".
        // 'position: 'average'' ajuda a centralizar no mouse.
        position: 'average', // 'average' ou 'nearest'
        intersect: false,

        // --- 2. Correção das Cores (Texto preto/Fundo preto) ---
        backgroundColor: '#0B1A33', // Azul Guardião
        titleColor: '#FFFFFF',
        bodyColor: '#FFFFFF',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        borderRadius: 8,
        padding: 10,
        displayColors: false, // Não mostra a "caixinha" de cor

        // --- 3. A NOVA LÓGICA (Mostrar Contagem) ---
        callbacks: {
          // Esta função constrói o texto dentro da tooltip
          label: (context) => {
            // Pega o item de dados completo (ex: {nome: 'Uber', valor: 50, count: 2})
            const item = chartData[context.dataIndex];
            if (!item) return '';

            const nome = item.nome;
            const valorFormatado = formatCurrency(item.valor);
            const contagem = item.count;
            const plural = contagem > 1 ? 'ões' : 'ão';

            // Cria o texto: "Uber: R$ 50,00 (2 transações)"
            return `${nome}: ${valorFormatado} (${contagem} transaç${plural})`;
          },
          title: () => null, // Remove o título
        },
      }
    },
    // Remove o "piscar" ao passar o mouse em cima de uma fatia
    onHover: (event, chartElement) => {
      if (chartElement.length) {
        event.native.target.style.cursor = 'pointer';
      } else {
        event.native.target.style.cursor = 'default';
      }
    }
  };
  // ----------------------------------------------------

  const formattedTotal = formatCurrency(totalValue);

  return (
    <div className="doughnut-chart-container">
      <div className="doughnut-chart-wrapper">
        {chartData && chartData.length > 0 && chartData.some(item => item.valor > 0) ? (
          <Doughnut data={data} options={options} />
        ) : (
          <div className="no-chart-data">
            <p>Sem dados para exibir.</p>
          </div>
        )}
        <div className="doughnut-center-text">
          <span className="total-amount">{formattedTotal}</span>
          <span className="label">{centerLabel}</span>
        </div>
      </div>
      <div className="chart-legend">
        {chartData && chartData.length > 0 ? (
          chartData.map((item, index) => (
            <div key={item.nome} className="legend-item">
              <span 
                className="legend-color" 
                style={{ backgroundColor: colorsPalette[index % colorsPalette.length] }}
              ></span>
              <span className="legend-label" style={{ color: colorsPalette[index % colorsPalette.length] }}>
                {item.nome}
              </span>
            </div>
          ))
        ) : (
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: 'var(--cor-texto-secundario)' }}></span>
            <span className="legend-label" style={{ color: 'var(--cor-texto-secundario)' }}>Nenhuma Categoria</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default DoughnutChart;