// Arquivo: frontend/src/components/DoughnutChart/DoughnutChart.jsx (VERSÃO V5.1 - CORREÇÃO DE SINTAXE)
/*
REATORAÇÃO (Missão V5.1 - Correção):
1. REMOVIDO o comentário '// <-- item.cor' da linha 99,
   que estava quebrando o parser do Vite (Erro 'Unexpected token').
*/

import React from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import './DoughnutChart.css';

/**
 * @param {object[]} chartData - Array de { nome: string, valor: number, count: number, cor: string }
 * @param {number} totalValue - O valor total para exibir no centro
 * @param {string} centerLabel - O texto do rótulo central
 */
function DoughnutChart({ chartData, totalValue, centerLabel }) {

  // A paleta hard-coded não é mais necessária

  const formatCurrency = (value) => {
    return (parseFloat(value) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const formattedTotal = formatCurrency(totalValue);

  // --- O Tooltip Customizado (Sem mudança) ---
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const plural = data.count > 1 ? 'ões' : 'ão';

      return (
        <div className="custom-tooltip">
          <p className="tooltip-label">{`${data.nome}: ${formatCurrency(data.valor)}`}</p>
          <p className="tooltip-sublabel">{`(${data.count} transaç${plural})`}</p>
        </div>
      );
    }
    return null;
  };
  // ---------------------------------------------

  return (
    <div className="doughnut-chart-container">
      <div className="doughnut-chart-wrapper">

        <ResponsiveContainer width="100%" height="100%">
          {chartData && chartData.length > 0 ? (
            <PieChart>
              <Tooltip
                coordinate={{ x: 0, y: 0 }} 
                offset={40} 
                cursor={false}
                wrapperStyle={{ zIndex: 1100, pointerEvents: 'none' }}
                content={<CustomTooltip />}
              />
              <Pie
                data={chartData}
                dataKey="valor"
                nameKey="nome"
                cx="50%"
                cy="50%"
                innerRadius="70%"
                outerRadius="100%"
                fill="#8884d8"
                paddingAngle={2}
              >
                {/* 1. A MUDANÇA: USANDO entry.cor */}
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.cor} />
                ))}
              </Pie>
            </PieChart>
          ) : (
            <div className="no-chart-data">
              <p>Sem dados para exibir.</p>
            </div>
          )}
        </ResponsiveContainer>

        {/* O texto central (Sem mudança) */}
        {chartData && chartData.length > 0 && (
          <div className="doughnut-center-text">
            <span className="total-amount">{formattedTotal}</span>
            <span className="label">{centerLabel}</span>
          </div>
        )}
      </div>

      {/* 2. A Legenda (USANDO entry.cor) */}
      {chartData && chartData.length > 0 && (
        <div className="chart-legend">
          {chartData.map((item) => (
            <div key={item.nome} className="legend-item">
              <span
                className="legend-color"
                style={{ backgroundColor: item.cor }} 
              ></span>
              {/* A CORREÇÃO ESTÁ AQUI: O comentário '//' foi removido 
                desta linha para corrigir o erro de sintaxe.
              */}
              <span className="legend-label" style={{ color: item.cor }}>
                {item.nome}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default DoughnutChart;