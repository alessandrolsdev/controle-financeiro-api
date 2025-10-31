// Arquivo: frontend/src/pages/Dashboard/Dashboard.jsx (VERSÃO FINAL COM ATUALIZAÇÃO)

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import './Dashboard.css';
import TransactionModal from '../../components/TransactionModal/TransactionModal';

function Dashboard() {
  const { logout } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // 1. TIRAMOS A FUNÇÃO DE DENTRO DO useEffect
  //    Agora ela pode ser chamada por qualquer um.
  const fetchDashboardData = async () => {
    const dataFim = new Date().toISOString().split('T')[0];
    const dataInicio = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
      .toISOString()
      .split('T')[0];

    try {
      setLoading(true);
      const response = await api.get('/dashboard/', {
        params: { data_inicio: dataInicio, data_fim: dataFim },
      });
      setData(response.data);
      setLoading(false);
    } catch (err) {
      console.error('Erro ao buscar dados do dashboard:', err);
      setError('Não foi possível carregar os dados.');
      setLoading(false);
    }
  };

  // 2. useEffect agora apenas CHAMA a função
  useEffect(() => {
    fetchDashboardData();
  }, []);

  // 3. A NOVA FUNÇÃO DE CALLBACK!
  //    Esta função será passada para o Modal.
  const handleSaveSuccess = () => {
    setIsModalOpen(false); // 1. Fecha o modal
    fetchDashboardData();     // 2. Busca os dados do dashboard novamente!
  };

  // ... (função renderContent continua igual) ...
  const renderContent = () => {
    if (loading) { return <p>Carregando dados...</p>; }
    if (error) { return <p className="error-message">{error}</p>; }
    if (data) {
      return (
        <div className="dashboard-stats">
          <div className="stat-card">
            <h3>Total Receitas</h3>
            <span className={data.total_receitas > 0 ? 'lucro' : ''}>R$ {data.total_receitas}</span>
          </div>
          <div className="stat-card">
            <h3>Total Gastos</h3>
            <span className={data.total_gastos > 0 ? 'gasto' : ''}>R$ {data.total_gastos}</span>
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
    return null;
  };

  return (
    <div className="dashboard-container">
      <nav className="dashboard-nav">
        {/* ... (código da nav existente) ... */}
      </nav>

      <header className="dashboard-header">
        <h2>Resumo dos Últimos 30 Dias</h2>
        <button onClick={() => setIsModalOpen(true)} className="add-transaction-button">
          + Registrar Transação
        </button>
      </header>

      <main className="dashboard-content">
        {renderContent()}
      </main>

      {/* 4. ATUALIZAÇÃO DA CHAMADA DO MODAL */}
      {isModalOpen && (
        <TransactionModal 
          onClose={() => setIsModalOpen(false)} 
          onSaveSuccess={handleSaveSuccess} // 5. Passa a nova função de callback
        />
      )}
    </div>
  );
}

export default Dashboard;