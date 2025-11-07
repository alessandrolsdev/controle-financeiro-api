// Arquivo: frontend/src/components/HorizontalBarChart/HorizontalBarChart.jsx
// (VERSÃO V4.6 - CORREÇÃO DE COR DINÂMICA)
/*
REATORAÇÃO (Missão V4.6):
1. O componente agora recebe a prop 'theme'.
2. Usa 'theme' para definir a cor dos eixos (stroke)
   com base no modo (light/dark).
*/

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import './HorizontalBarChart.css';

/**
 * @param {object[]} data - Array de { nome: string, valor: number, count: number }
 * @param {string} theme - 'light' ou 'dark'
 */
function HorizontalBarChart({ data, theme }) { // <-- RECEBE O TEMA

  // Cor dinâmica do eixo X/Y
  const axisColor = theme === 'dark' ? '#CED4DA' : '#6C757D'; 

  const colorsPalette = [
    '#FF7A00', 
    '#D400E6',
    '#00E08F',
    '#FFC107', '#20C997', '#6F42C1',
  ];

  const formatCurrency = (value) => {
    return (parseFloat(value) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };
  
  const formatXAxisTicks = (tickItem) => {
    if (tickItem >= 1000) {
      return `R$ ${Math.round(tickItem / 1000)}k`;
    }
    if (tickItem > 0) {
        return `R$ ${tickItem.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}`;
    }
    return `R$ 0`;
  };

  const CustomTooltip = ({ active, payload }) => { /* ... (sem mudança) ... */
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const plural = data.count > 1 ? 'ões' : 'ão';

      return (
        <div className="horizontal-bar-tooltip">
          <p className="tooltip-label">{`${data.nome}: ${formatCurrency(data.valor)}`}</p>
          <p className="tooltip-sublabel">{`(${data.count} transaç${plural})`}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="horizontal-bar-wrapper">
      <ResponsiveContainer width="100%" height={data.length * 45 + 20}>
        <BarChart
          data={data}
          layout="vertical" 
          margin={{ top: 0, right: 30, left: 10, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--cor-borda)" />
          
          <XAxis 
            type="number" 
            stroke={axisColor} // <-- DINÂMICO
            tickFormatter={formatXAxisTicks}
            axisLine={false}
            tickLine={false}
          />
          
          <YAxis 
            type="category" 
            dataKey="nome"
            stroke={axisColor} // <-- DINÂMICO
            width={100}
            axisLine={false}
            tickLine={false}
          />
          
          <Tooltip 
            cursor={{ fill: 'rgba(255, 255, 255, 0.1)' }}
            wrapperStyle={{ zIndex: 1100, pointerEvents: 'none' }}
            content={<CustomTooltip />}
          />
          
          <Bar dataKey="valor" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={colorsPalette[index % colorsPalette.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default HorizontalBarChart;