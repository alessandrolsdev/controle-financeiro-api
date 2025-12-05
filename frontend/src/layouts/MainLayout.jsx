// Arquivo: frontend/src/layouts/MainLayout.jsx
/**
 * @file Layout Principal (Componente Pai).
 * @description Gerencia a estrutura das páginas protegidas, controla filtros globais, estado do modal de transações e busca de dados do dashboard.
 */

import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from '../components/Navbar/Navbar';
import TransactionModal from '../components/TransactionModal/TransactionModal';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

/**
 * Formata um objeto Date para uma string 'YYYY-MM-DD'.
 * @param {Date} date - O objeto de data.
 * @returns {string} A data formatada.
 */
const formatDateForAPI = (date) => {
  const dateObj = new Date(date);
  const year = dateObj.getFullYear();
  const month = (dateObj.getMonth() + 1).toString().padStart(2, '0');
  const day = dateObj.getDate().toString().padStart(2, '0');
  return `${year}-${month}-${day}`;
};

/**
 * Componente de Layout Principal.
 *
 * Envolve todas as rotas protegidas da aplicação.
 * Responsável por:
 * - Buscar dados do dashboard.
 * - Gerenciar filtros de data.
 * - Controlar a exibição do modal de transações.
 * - Renderizar a barra de navegação (Navbar).
 * - Passar contexto global para rotas filhas via Outlet.
 *
 * @returns {JSX.Element} O layout renderizado.
 */
function MainLayout() {
  // --- Estados de Dados do Dashboard ---
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // --- Estados do Contexto de Autenticação ---
  const { syncTrigger, isAuthLoading } = useAuth(); 

  // --- Estados do Filtro Global ---
  const [filterType, setFilterType] = useState('daily');
  const [dataInicio, setDataInicio] = useState(new Date());
  const [dataFim, setDataFim] = useState(new Date());       
  
  const [dataInicioStr, setDataInicioStr] = useState('');
  const [dataFimStr, setDataFimStr] = useState('');

  // --- Estados do Modal ---
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState(null);

  /**
   * Efeito colateral que calcula a data final (dataFim) com base no tipo de filtro e data inicial.
   * Evita loops de atualização se o filtro for 'personalizado'.
   */
  useEffect(() => {
    if (filterType === 'personalizado') return;

    let dataFimCalculada;
    const dataBase = new Date(dataInicio.getFullYear(), dataInicio.getMonth(), dataInicio.getDate());

    switch (filterType) {
      case 'weekly':
        dataFimCalculada = new Date(dataBase);
        dataFimCalculada.setDate(dataFimCalculada.getDate() + 6);
        break;
      case 'monthly':
        dataFimCalculada = new Date(dataBase.getFullYear(), dataBase.getMonth() + 1, 0);
        break;
      case 'yearly':
        dataFimCalculada = new Date(dataBase.getFullYear(), 11, 31);
        break;
      case 'daily':
      default:
        dataFimCalculada = dataBase; 
        break;
    }
    setDataFim(dataFimCalculada);

  }, [filterType, dataInicio]);


  /**
   * Efeito colateral que converte as datas para o formato de string da API.
   */
  useEffect(() => {
    setDataInicioStr(formatDateForAPI(dataInicio));
    setDataFimStr(formatDateForAPI(dataFim));
  }, [dataInicio, dataFim]); 


  /**
   * Busca os dados consolidados do dashboard na API.
   * Utiliza os parâmetros de data inicial e final convertidos.
   */
  const fetchDashboardData = async () => {
    if (!dataInicioStr || !dataFimStr) return;
    
    try {
      setLoading(true);
      const response = await api.get('/dashboard/', {
        params: { 
          data_inicio: dataInicioStr, 
          data_fim: dataFimStr
        },
      });
      setData(response.data);
      setLoading(false);
    } catch (err) {
      console.error('Erro ao buscar dados do dashboard:', err);
      setError('Não foi possível carregar os dados.');
      setLoading(false);
    }
  };
  
  /**
   * Efeito colateral que dispara a busca de dados.
   * Depende das datas, do gatilho de sincronização offline e do estado de autenticação.
   */
  useEffect(() => {
    if (!dataInicioStr || !dataFimStr || isAuthLoading) return;
    
    fetchDashboardData();
  }, [dataInicioStr, dataFimStr, syncTrigger, isAuthLoading]);
  
  // --- FUNÇÕES DE CONTROLE DO MODAL ---

  /**
   * Abre o modal de transação em modo de criação.
   */
  const handleAddTransactionClick = () => {
    setEditingTransaction(null);
    setIsModalOpen(true);
  };

  /**
   * Abre o modal de transação em modo de edição.
   * @param {object} transaction - Objeto contendo os dados da transação a ser editada.
   */
  const handleEditClick = (transaction) => {
    setEditingTransaction(transaction);
    setIsModalOpen(true);
  };

  /**
   * Callback executado após salvar uma transação com sucesso.
   * Atualiza os dados do dashboard instantaneamente.
   * @param {object} novosDadosDoDashboard - Dados atualizados do dashboard retornados pela API.
   */
  const handleSaveSuccess = (novosDadosDoDashboard) => {
    setIsModalOpen(false); 
    setEditingTransaction(null);
    setData(novosDadosDoDashboard);
  };
  
  /**
   * Callback executado após excluir uma transação com sucesso.
   * Atualiza os dados do dashboard.
   * @param {object} novosDadosDoDashboard - Dados atualizados do dashboard.
   */
  const handleDeleteSuccess = (novosDadosDoDashboard) => {
    setData(novosDadosDoDashboard);
  };

  /**
   * Fecha o modal e limpa o estado de edição.
   */
  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingTransaction(null);
  };

  if (isAuthLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: 'white', fontFamily: 'Montserrat', backgroundColor: '#0B1A33' }}>
        Carregando aplicação...
      </div>
    );
  }

  return (
    <div className="layout-container">
      <main className="layout-content">
        <Outlet context={{ 
          data, 
          loading, 
          error,
          filterType,
          setFilterType,
          dataInicio,
          setDataInicio,
          dataFim,
          setDataFim,
          dataInicioStr,  
          dataFimStr,
          handleEditClick,
          handleDeleteSuccess
        }} />
      </main>

      <Navbar onAddTransaction={handleAddTransactionClick} />

      {isModalOpen && (
        <TransactionModal 
          onClose={handleCloseModal}
          onSaveSuccess={handleSaveSuccess}
          transactionToEdit={editingTransaction}
          dataInicioStr={dataInicioStr}
          dataFimStr={dataFimStr}
        />
      )}
    </div>
  );
}

export default MainLayout;
