// Arquivo: frontend/src/layouts/MainLayout.jsx
// (VERSÃO V3.0 - O "Pai" que busca os dados)

import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from '../components/Navbar/Navbar';
import TransactionModal from '../components/TransactionModal/TransactionModal';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

function MainLayout() {
  // --- LÓGICA DE DADOS (Agora mora no "Pai") ---
  const [data, setData] = useState(null); // Armazena os dados do /dashboard/
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Pega a "campainha" de sincronização do AuthContext
  const { syncTrigger } = useAuth(); 

  /**
   * Função principal que busca os dados do backend.
   */
  const fetchDashboardData = async () => {
    // Busca dos últimos 30 dias
    const dataFim = new Date().toISOString().split('T')[0];
    const dataInicio = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    try {
      setLoading(true);
      const response = await api.get('/dashboard/', {
        params: { data_inicio: dataInicio, data_fim: dataFim },
      });
      setData(response.data); // Salva os dados no estado
      setLoading(false);
    } catch (err) {
      console.error('Erro ao buscar dados do dashboard:', err);
      setError('Não foi possível carregar os dados.');
      setLoading(false);
    }
  };

  /**
   * O "Ouvido" do Layout.
   * Roda quando o app carrega E quando a "campainha" (syncTrigger) toca.
   */
  useEffect(() => {
    fetchDashboardData();
  }, [syncTrigger]); // <-- Ouve a campainha!

  
  // --- LÓGICA DO MODAL ---
  const [isModalOpen, setIsModalOpen] = useState(false);

  /**
   * Chamado pelo Navbar (botão "+")
   */
  const handleAddTransactionClick = () => {
    setIsModalOpen(true);
  };

  /**
   * Chamado pelo TransactionModal (quando o 'api.post' dá certo)
   * @param {object} novosDadosDoDashboard - Os dados atualizados que o backend retornou
   */
  const handleSaveSuccess = (novosDadosDoDashboard) => {
    setIsModalOpen(false); // 1. Fecha o modal
    setData(novosDadosDoDashboard); // 2. ATUALIZA O ESTADO com os novos dados
  };

  return (
    <div className="layout-container">
      <main className="layout-content">
        {/* O 'Outlet' é o "buraco" onde o Dashboard ou Settings vão aparecer.
            Usamos 'context' para "entregar" os dados para o filho que
            estiver lá dentro. */}
        <Outlet context={{ data, loading, error, fetchDashboardData }} />
      </main>

      {/* A Navbar fica fixa no rodapé */}
      <Navbar onAddTransaction={handleAddTransactionClick} />

      {/* O Modal (controlado pelo Pai) */}
      {isModalOpen && (
        <TransactionModal 
          onClose={() => setIsModalOpen(false)} 
          onSaveSuccess={handleSaveSuccess} 
        />
      )}
    </div>
  );
}

export default MainLayout;