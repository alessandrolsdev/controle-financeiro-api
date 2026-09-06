// Arquivo: frontend/src/components/DoughnutChart/DoughnutChart.jsx
/**
 * @file Gráfico de Rosca (Doughnut).
 * @description Componente para visualização de dados financeiros em formato de gráfico de rosca, com cores dinâmicas e tooltip personalizado.
 */

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import "./DoughnutChart.css";

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
    return (parseFloat(value) || 0).toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL",
    });
  };

  const formattedTotal = formatCurrency(totalValue);

  /**
   * Tooltip personalizado para exibir informações detalhadas ao passar o mouse sobre uma fatia.
   */
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const plural = data.count > 1 ? "ões" : "ão";

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
      {!chartData || chartData.length === 0 ? (
        <p className="vazio">Sem dados no período.</p>
      ) : (
        <>
          <div className="rosca">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Tooltip
                  coordinate={{ x: 0, y: 0 }}
                  offset={40}
                  cursor={false}
                  wrapperStyle={{ zIndex: 1100, pointerEvents: "none" }}
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
                  paddingAngle={2}
                >
                  {chartData.map((entry) => (
                    <Cell key={entry.nome} fill={entry.cor} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>

            <div className="rosca-centro">
              <span className="rosca-rotulo">{centerLabel}</span>
              <span className="rosca-valor">{formattedTotal}</span>
            </div>
          </div>

          <ul className="rosca-legenda">
            {chartData.map((item) => (
              <li key={item.nome}>
                <span
                  style={{ backgroundColor: item.cor }}
                  aria-hidden="true"
                />
                {item.nome}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export default DoughnutChart;
