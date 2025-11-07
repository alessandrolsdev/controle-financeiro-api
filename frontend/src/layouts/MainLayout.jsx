// Arquivo: frontend/src/layouts/MainLayout.jsx
// (VERSÃO V6.1 - CORREÇÃO DEFINITIVA DO LOOP INFINITO)
/*
REATORAÇÃO (Missão V6.1 - Correção):
Este é o 'merge' correto.
1. Contém a lógica de Edição (V6.0) 'editingTransaction'.
2. Contém a lógica de 'useEffect' (V3.9) que NÃO causa o loop
   'Maximum update depth exceeded'. O 'useEffect' principal
   NÃO chama 'setDataInicio'.
*/

import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from '../components/Navbar/Navbar';
import TransactionModal from '../components/TransactionModal/TransactionModal';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

/**
 * Função auxiliar para formatar datas para a API (AAAA-MM-DD)
 */
const formatDateForAPI = (date) => {
  const dateObj = new Date(date);
  const year = dateObj.getFullYear();
  const month = (dateObj.getMonth() + 1).toString().padStart(2, '0');
  const day = dateObj.getDate().toString().padStart(2, '0');
  return `${year}-${month}-${day}`;
};

function MainLayout() {
  // --- LÓGICA DE DADOS ---
  const [data, setData] = useState(null); 
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { syncTrigger } = useAuth(); 

  // --- NOSSOS ESTADOS DE FILTRO ---
  const [filterType, setFilterType] = useState('daily');
  const [dataInicio, setDataInicio] = useState(new Date());
  const [dataFim, setDataFim] = useState(new Date());       
  
  const [dataInicioStr, setDataInicioStr] = useState('');
  const [dataFimStr, setDataFimStr] = useState('');

  // --- LÓGICA DO MODAL (V6.0) ---
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState(null);

  /**
   * Efeito 1: Calcula o 'dataFim' (A VERSÃO CORRIGIDA V3.9)
   * Roda quando 'filterType' ou 'dataInicio' mudam.
   * NÃO causa loops, pois não chama 'setDataInicio'.
   */
  useEffect(() => {
    // Se o filtro for personalizado, o 'dataFim' é controlado
    // pelo usuário no FilterControls.
    if (filterType === 'personalizado') return;

    let dataFimCalculada;
    // Usa a data de início (que o FilterControls definiu) como base
    const dataBase = new Date(dataInicio.getFullYear(), dataInicio.getMonth(), dataInicio.getDate());

    switch (filterType) {
      case 'weekly':
        // A data de início já foi definida para o início da semana
        // pelo FilterControls, então apenas calculamos o fim.
        dataFimCalculada = new Date(dataBase);
        dataFimCalculada.setDate(dataFimCalculada.getDate() + 6);
        break;
      case 'monthly':
        // A data de início já é dia 1
        dataFimCalculada = new Date(dataBase.getFullYear(), dataBase.getMonth() + 1, 0);
        break;
      case 'yearly':
        // A data de início já é 1º de Jan
        dataFimCalculada = new Date(dataBase.getFullYear(), 11, 31);
        break;
      case 'daily':
      default:
        dataFimCalculada = dataBase; 
        break;
    }
    // Atualiza APENAS o 'dataFim'
    setDataFim(dataFimCalculada);

  }, [filterType, dataInicio]); // <-- Ouve 'dataInicio', mas não o define


  /**
   * Efeito 2: Converte as datas (Date objects) para Strings (AAAA-MM-DD)
   * (Sem mudança)
   */
  useEffect(() => {
    setDataInicioStr(formatDateForAPI(dataInicio));
    setDataFimStr(formatDateForAPI(dataFim));
  }, [dataInicio, dataFim]); 


  /**
   * Função principal que busca os dados do backend.
   * (Sem mudança)
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
   * Efeito 3: Busca os dados
   * (Sem mudança)
   */
  useEffect(() => {
    fetchDashboardData();
  }, [dataInicioStr, dataFimStr, syncTrigger]);
  
  // --- FUNÇÕES DE CONTROLE DO MODAL (V6.0) ---

  /**
   * Chamado pelo botão '+' da Navbar (Modo de Criação)
   */
  const handleAddTransactionClick = () => {
    setEditingTransaction(null);
    setIsModalOpen(true);
  };

  /**
   * Chamado pelo botão 'Editar' no Dashboard.jsx (Modo de Edição)
   */
  const handleEditClick = (transaction) => {
    setEditingTransaction(transaction);
    setIsModalOpen(true);
  };

  /**
   * Chamado quando o modal é salvo
   */
  const handleSaveSuccess = () => {
    setIsModalOpen(false); 
    setEditingTransaction(null);
    fetchDashboardData(); // Força o recarregamento dos dados
  };

  /**
   * Chamado quando o modal é fechado pelo 'X'
   */
  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingTransaction(null);
  };


  return (
    <div className="layout-container">
      <main className="layout-content">
        {/* Passa TODOS os estados e setters para os Filhos */}
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
          handleEditClick // <-- Prop de Edição (V6.0)
        }} />
      </main>

      {/* Navbar (V6.0) */}
      <Navbar onAddTransaction={handleAddTransactionClick} />

      {/* Modal (V6.0) */}
      {isModalOpen && (
        <TransactionModal 
          onClose={handleCloseModal}
          onSaveSuccess={handleSaveSuccess}
          transactionToEdit={editingTransaction}
        />
      )}
    </div>
  );
}

export default MainLayout;