// Arquivo: frontend/src/components/HorizontalBarChart/HorizontalBarChart.jsx
"""
Componente Reutilizável de Gráfico de Barras Horizontais (V5.0).

Este componente renderiza um gráfico de barras horizontais
usando a biblioteca 'recharts'. É usado na página 'Reports.jsx'
para mostrar Gastos e Receitas por categoria.

Decisão de Arquitetura (V5.0 - Cores Dinâmicas):
Este gráfico usa a cor exata ('cor') definida pelo usuário
para cada categoria, que é passada nos dados ('chartData').

Decisão de Arquitetura (V4.6 - Tema):
Este gráfico é "theme-aware" (consciente do tema). Ele recebe
o 'theme' (light/dark) como prop para definir a cor
do texto dos eixos (SVG), que o CSS não pode alcançar.
"""

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import './HorizontalBarChart.css'; // (CSS para o tooltip customizado)

/**
 * Renderiza um gráfico de barras horizontais dinâmico.
 *
 * @param {object} props
 * @param {Array<object>} props.data - Array de dados.
 * Formato esperado: [{ nome: string, valor: number, count: number, cor: string }]
 * @param {string} props.theme - 'light' ou 'dark' (vindo do 'useTheme()').
 */
function HorizontalBarChart({ data, theme }) {

  // A paleta hard-coded NÃO É MAIS NECESSÁRIA!
  
  // Define a cor do texto dos eixos (SVG) com base no tema (V4.6)
  // (Valores do 'index.css')
  const axisColor = theme === 'dark' ? '#CED4DA' : '#6C757D'; 

  // --- Funções Auxiliares ---

  const formatCurrency = (value) => {
    return (parseFloat(value) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };
  
  // Formata os "ticks" do eixo (ex: R$ 0.1k ou R$ 10k)
  const formatXAxisTicks = (tickItem) => {
    if (tickItem >= 1000) {
      return `R$ ${Math.round(tickItem / 1000)}k`;
    }
    if (tickItem > 0) {
        // Formata valores pequenos como "R$ 271,02" (removido '.toLocaleString' para simplicidade)
        return `R$ ${tickItem}`; 
    }
    return `R$ 0`;
  };

  /**
   * Componente React customizado para o Tooltip (pop-up) do 'recharts'.
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
  // ---------------------------------------------

  return (
    <div className="horizontal-bar-wrapper">
      {/* Decisão de Engenharia:
        A altura do gráfico é dinâmica, baseada em quantos
        itens (barras) existem. (45px por barra + 20px de "chão").
      */}
      <ResponsiveContainer width="100%" height={data.length * 45 + 20}>
        <BarChart
          data={data}
          layout="vertical" // <-- A "mágica" para fazê-lo horizontal
          margin={{ top: 0, right: 30, left: 10, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--cor-borda)" />
          
          {/* Eixo X (Horizontal) - Os Valores (R$) */}
          <XAxis 
            type="number" 
            stroke={axisColor} // <-- Cor dinâmica (V4.6)
            tickFormatter={formatXAxisTicks}
            axisLine={false}
            tickLine={false}
          />
          
          {/* Eixo Y (Vertical) - As Categorias (Nomes) */}
          <YAxis 
            type="category" 
            dataKey="nome" // Usa a 'nome' (que virá de 'nome_categoria')
            stroke={axisColor} // <-- Cor dinâmica (V4.6)
            width={100} // Espaço para os nomes (ex: "Combustível")
            axisLine={false}
            tickLine={false}
          />
          
          <Tooltip 
            cursor={{ fill: 'rgba(255, 255, 255, 0.1)' }} // Efeito de hover "glass"
            wrapperStyle={{ zIndex: 1100, pointerEvents: 'none' }}
            content={<CustomTooltip />}
          />
          
          {/* A Barra */}
          <Bar dataKey="valor" radius={[0, 4, 4, 0]}>
            {/* Decisão de Engenharia (V5.0):
              Usa 'entry.cor' (vindo do DB) para colorir
              cada barra (<Cell>) dinamicamente.
            */}
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