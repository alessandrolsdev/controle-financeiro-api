// Arquivo: frontend/src/components/DoughnutChart/DoughnutChart.jsx
"""
Componente Reutilizável de Gráfico de Rosca (Doughnut).

Este componente renderiza um gráfico de rosca (PieChart com innerRadius)
usando a biblioteca 'recharts'.

Decisão de Arquitetura (V5.0 - Cores Dinâmicas):
Este gráfico é "data-driven". Ele não tem uma paleta de cores
fixa. Ele usa o campo 'cor' que é fornecido nos dados
('chartData'), que o backend buscou do banco de dados.
"""

import React from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import './DoughnutChart.css'; // (CSS para o texto central, legenda e tooltip)

/**
 * Renderiza um gráfico de rosca dinâmico.
 *
 * @param {object} props
 * @param {Array<object>} props.chartData - Array de dados.
 * Formato esperado: [{ nome: string, valor: number, count: number, cor: string }]
 * @param {number} props.totalValue - O valor total (ex: 5512.00) para exibir no centro.
 * @param {string} props.centerLabel - O texto (ex: "Total Gasto") para exibir no centro.
 */
function DoughnutChart({ chartData, totalValue, centerLabel }) {

  // --- Funções Auxiliares ---

  const formatCurrency = (value) => {
    return (parseFloat(value) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const formattedTotal = formatCurrency(totalValue);

  /**
   * Componente React customizado para o Tooltip (pop-up) do 'recharts'.
   * Isso nos permite estilizar o tooltip (via CSS) e mostrar
   * a contagem de transações, o que o padrão não faz.
   */
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      // 'payload[0].payload' é onde o Recharts armazena
      // o objeto de dados original da "fatia"
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
          {/* Renderização Condicional:
              Só renderiza o gráfico se houver dados. */}
          {chartData && chartData.length > 0 ? (
            <PieChart>
              <Tooltip
                coordinate={{ x: 0, y: 0 }} 
                offset={40} 
                cursor={false} // Impede o "flicker" do mouse
                wrapperStyle={{ zIndex: 1100, pointerEvents: 'none' }} // Faz o tooltip seguir o mouse
                content={<CustomTooltip />} // Usa nosso componente customizado
              />
              <Pie
                data={chartData}
                dataKey="valor" // Chave usada para o tamanho da fatia
                nameKey="nome"  // Chave usada para o nome (no tooltip)
                cx="50%"
                cy="50%"
                innerRadius="70%" // O "buraco" do donut
                outerRadius="100%"
                fill="#8884d8" // Cor padrão (sobrescrita pelo <Cell>)
                paddingAngle={2} // Espaço entre as fatias
              >
                {/* Decisão de Engenharia (V5.0):
                  Mapeia os dados e usa 'entry.cor' (vindo do DB)
                  para colorir cada fatia (<Cell>) dinamicamente.
                */}
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.cor} />
                ))}
              </Pie>
            </PieChart>
          ) : (
            // (V2.7) O "Estado Vazio"
            <div className="no-chart-data">
              <p>Sem dados para exibir.</p>
            </div>
          )}
        </ResponsiveContainer>

        {/* O Texto Central (R$ 0,00):
          Renderizado via CSS (position: absolute) por cima do gráfico.
          Só aparece se houver dados.
        */}
        {chartData && chartData.length > 0 && (
          <div className="doughnut-center-text">
            <span className="total-amount">{formattedTotal}</span>
            <span className="label">{centerLabel}</span>
          </div>
        )}
      </div>

      {/* A Legenda Customizada (V5.0):
        Renderizada manualmente (não pelo 'recharts') para
        garantir o controle total do estilo e das cores.
      */}
      {chartData && chartData.length > 0 && (
        <div className="chart-legend">
          {chartData.map((item) => (
            <div key={item.nome} className="legend-item">
              <span
                className="legend-color"
                style={{ backgroundColor: item.cor }} // <-- Cor dinâmica do DB
              ></span>
              <span className="legend-label" style={{ color: item.cor }}> {/* <-- Cor dinâmica do DB */}
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