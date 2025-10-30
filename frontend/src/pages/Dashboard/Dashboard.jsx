// Arquivo: frontend/src/pages/Dashboard/Dashboard.jsx (Versão com Dados)

import React, { useState, useEffect } from 'react'; // Importa useState e useEffect
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api'; // Importa nosso novo serviço de API
import './Dashboard.css';

function Dashboard() {
  const { logout } = useAuth();
  
  // 1. Criamos estados para guardar os dados do dashboard
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 2. Hook useEffect para buscar dados quando o componente carregar
  useEffect(() => {
    const fetchDashboardData = async () => {
      // Pega as datas de hoje e 30 dias atrás
      const dataFim = new Date().toISOString().split('T')[0]; // Formato AAAA-MM-DD
      const dataInicio = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0]; // 30 dias atrás

      try {
        setLoading(true);
        // 3. USA NOSSA API!
        // Nosso 'api.js' vai adicionar o token automaticamente!
        const response = await api.get('/dashboard/', {
          params: {
            data_inicio: dataInicio,
            data_fim: dataFim,
          },
        });
        
        setData(response.data); // Salva os dados no estado
        setLoading(false);
      } catch (err) {
        console.error('Erro ao buscar dados do dashboard:', err);
        setError('Não foi possível carregar os dados.');
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []); // O array vazio [] significa "execute isso apenas uma vez, quando o componente montar"

  // 4. Renderização condicional
  const renderContent = () => {
    if (loading) {
      return <p>Carregando dados...</p>;
    }

    if (error) {
      return <p className="error-message">{error}</p>;
    }

    if (data) {
      return (
        <div className="dashboard-stats">
          <div className="stat-card">
            <h3>Total Receitas</h3>
            <span>R$ {data.total_receitas}</span>
          </div>
          <div className="stat-card">
            <h3>Total Gastos</h3>
            <span className="gasto">R$ {data.total_gastos}</span>
          </div>
          <div className="stat-card">
            <h3>Lucro Líquido</h3>
            <span className={data.lucro_liquido >= 0 ? 'lucro' : 'gasto'}>
              R$ {data.lucro_liquido}
            </span>
          </div>
          <div className="gastos-categoria">
            <h3>Gastos por Categoria</h3>
            <ul>
              {data.gastos_por_categoria.length > 0 ? (
                data.gastos_por_categoria.map((item) => (
                  <li key={item.nome_categoria}>
                    <span>{item.nome_categoria}</span>
                    <span className="gasto">R$ {item.valor_total}</span>
                  </li>
                ))
              ) : (
                <p>Nenhum gasto registrado neste período.</p>
              )}
            </ul>
          </div>
        </div>
      );
    }
    
    return null; // Caso algo dê errado
  };

  return (
    <div className="dashboard-container">
      <nav className="dashboard-nav">
        <h1>Meu Painel Financeiro</h1>
        <button onClick={logout} className="logout-button">
          Sair
        </button>
      </nav>
      <main className="dashboard-content">
        <h2>Resumo dos Últimos 30 Dias</h2>
        {renderContent()}
      </main>
    </div>
  );
}

export default Dashboard;