// Arquivo: frontend/src/components/DoughnutChart/DoughnutChart.jsx
/**
 * @file Gráfico de Rosca (Doughnut).
 * @description Componente para visualização de dados financeiros em formato de gráfico de rosca, com cores dinâmicas e tooltip personalizado.
 */

import React from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import './DoughnutChart.css';

/**
 * Componente de Gráfico de Rosca.
 *
 * Exibe a distribuição de valores por categoria. O centro do gráfico exibe o valor total acumulado.
 * As cores das fatias são definidas nos dados de entrada.
 *
 * @param {object} props - Propriedades do componente.
 * @param {Array<object>} props.chartData - Dados do gráfico, contendo valor, cor e nome por categoria.
 * @param {number} props.totalValue - O valor total a ser exibido no centro.
 * @param {string} props.centerLabel - Rótulo descritivo para o valor central.
 * @returns {JSX.Element} O gráfico renderizado.
 */
function DoughnutChart({ chartData, totalValue, centerLabel }) {

  /**
   * Formata valor numérico para moeda brasileira (BRL).
   */
  const formatCurrency = (value) => {
    return (parseFloat(value) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const formattedTotal = formatCurrency(totalValue);

  /**
   * Tooltip personalizado para exibir informações detalhadas ao passar o mouse sobre uma fatia.
   */
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

        {chartData && chartData.length > 0 && (
          <div className="doughnut-center-text">
            <span className="total-amount">{formattedTotal}</span>
            <span className="label">{centerLabel}</span>
          </div>
        )}
      </div>

      {chartData && chartData.length > 0 && (
        <div className="chart-legend">
          {chartData.map((item) => (
            <div key={item.nome} className="legend-item">
              <span
                className="legend-color"
                style={{ backgroundColor: item.cor }}
              ></span>
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
