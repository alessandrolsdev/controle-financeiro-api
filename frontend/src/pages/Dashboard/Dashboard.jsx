// Arquivo: frontend/src/pages/Dashboard/Dashboard.jsx (VERSÃO FINAL SINCRONIZADA)
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

  // 1. A FUNÇÃO DE BUSCAR DADOS (usada no carregamento inicial)
  const fetchDashboardData = async () => {
    const dataFim = new Date().toISOString().split('T')[0];
    const dataInicio = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    try {
      setLoading(true);
      // O cache buster não é mais necessário aqui, mas não faz mal
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

  // 2. O useEffect (roda só uma vez, no carregamento)
  useEffect(() => {
    fetchDashboardData();
  }, []); 

  // --- A MUDANÇA ESTÁ AQUI ---
  // 3. O CALLBACK QUE ATUALIZA O ESTADO (A CORREÇÃO DA CONDIÇÃO DE CORRIDA)
  const handleSaveSuccess = (novosDadosDoDashboard) => {
    setIsModalOpen(false); // Fecha o modal
    setData(novosDadosDoDashboard); // 4. ATUALIZA O ESTADO com os dados do filho!
  };
  // ------------------------------

  // Função para renderizar o conteúdo (com formatação de moeda)
  const renderContent = () => {
    if (loading) { return <p>Carregando dados...</p>; }
    if (error) { return <p className="error-message">{error}</p>; }
    if (data) {
      const formatCurrency = (value) => {
        const number = parseFloat(value) || 0;
        return number.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
      };

      return (
        <div className="dashboard-stats">
          <div className="stat-card">
            <h3>Total Receitas</h3>
            <span className={data.total_receitas > 0 ? 'lucro' : ''}>{formatCurrency(data.total_receitas)}</span>
          </div>
          <div className="stat-card">
            <h3>Total Gastos</h3>
            <span className={data.total_gastos > 0 ? 'gasto' : ''}>{formatCurrency(data.total_gastos)}</span>
          </div>
          <div className="stat-card">
            <h3>Lucro Líquido</h3>
            <span className={data.lucro_liquido >= 0 ? 'lucro' : 'gasto'}>{formatCurrency(data.lucro_liquido)}</span>
          </div>
          <div className="gastos-categoria">
            <h3>Gastos por Categoria</h3>
            <ul>
              {data.gastos_por_categoria.length > 0 ? (
                data.gastos_por_categoria.map((item) => (
                  <li key={item.nome_categoria}>
                    <span>{item.nome_categoria}</span>
                    <span className="gasto">{formatCurrency(item.valor_total)}</span>
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

  // O JSX para renderizar a página
  return (
    <div className="dashboard-container">
      <nav className="dashboard-nav">
        <h1>Meu Painel Financeiro</h1>
        <div>
          <Link to="/settings" className="nav-link">
            Configurações
          </Link>
          <button onClick={logout} className="logout-button">
            Sair
          </button>
        </div>
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

      {/* AQUI ESTÁ A CONEXÃO ENTRE PAI E FILHO */}
      {isModalOpen && (
        <TransactionModal 
          onClose={() => setIsModalOpen(false)} 
          onSaveSuccess={handleSaveSuccess} 
        />
      )}
    </div>
  );
}
export default Dashboard;