// Arquivo: frontend/src/components/HorizontalBarChart/HorizontalBarChart.jsx
/**
 * @file Gráfico de Barras Horizontais.
 * @description Componente para visualização de dados em formato de barras horizontais, adaptado para tema claro/escuro e cores dinâmicas.
 */

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import './HorizontalBarChart.css';

/**
 * Componente de Gráfico de Barras Horizontais.
 *
 * Exibe gastos ou receitas discriminados por categoria. As cores das barras são definidas
 * dinamicamente nos dados de entrada. Ajusta a cor dos eixos conforme o tema selecionado.
 *
 * @param {object} props - Propriedades do componente.
 * @param {Array<object>} props.data - Array de dados contendo nome, valor, contagem e cor.
 * @param {string} props.theme - O tema atual ('light' ou 'dark') para estilização dos eixos.
 * @returns {JSX.Element} O gráfico renderizado.
 */
function HorizontalBarChart({ data, theme }) {

  const axisColor = theme === 'dark' ? '#CED4DA' : '#6C757D'; 

  /**
   * Formata valores monetários para BRL.
   */
  const formatCurrency = (value) => {
    return (parseFloat(value) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };
  
  /**
   * Formata os valores exibidos no eixo X para abreviar números grandes.
   */
  const formatXAxisTicks = (tickItem) => {
    if (tickItem >= 1000) {
      return `R$ ${Math.round(tickItem / 1000)}k`;
    }
    if (tickItem > 0) {
        return `R$ ${tickItem.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}`;
    }
    return `R$ 0`;
  };

  /**
   * Tooltip personalizado para exibir detalhes ao passar o mouse.
   */
  const CustomTooltip = ({ active, payload }) => {
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
            stroke={axisColor}
            tickFormatter={formatXAxisTicks}
            axisLine={false}
            tickLine={false}
          />
          
          <YAxis 
            type="category" 
            dataKey="nome"
            stroke={axisColor}
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
              <Cell key={`cell-${index}`} fill={entry.cor} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default HorizontalBarChart;
