// Arquivo: frontend/src/layouts/MainLayout.jsx
// (VERSÃO V-REVERTIDA - SÍNCRONA/GRATUITA)
/*
REVERSÃO (MISSÃO DE DEPLOY GRATUITO):
Revertemos este arquivo para a arquitetura "V1.0" Síncrona.

1. 'handleSaveSuccess' agora ACEITA 'novosDadosDoDashboard'
   (vindos diretamente da resposta da API).
2. Ele chama 'setData(novosDadosDoDashboard)' (atualização instantânea).
3. Ele NÃO chama mais 'fetchDashboardData()' (removendo a 2ª chamada de API).
4. O modal 'TransactionModal' agora recebe 'dataInicioStr' e 'dataFimStr'
   para que ele possa enviá-los para o backend.
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
   * Efeito 1: Calcula o 'dataFim' (V3.9)
   */
  useEffect(() => {
    if (filterType === 'personalizado') return;
    let dataFimCalculada;
    const dataBase = new Date(dataInicio.getFullYear(), dataInicio.getMonth(), dataInicio.getDate());

    switch (filterType) {
      case 'weekly':
        const diaDaSemana = dataBase.getDay();
        const diff = dataBase.getDate() - diaDaSemana + (diaDaSemana === 0 ? -6 : 1);
        const inicioSemana = new Date(dataBase.setDate(diff));
        dataFimCalculada = new Date(inicioSemana);
        dataFimCalculada.setDate(dataFimCalculada.getDate() + 6);
        setDataInicio(inicioSemana); 
        break;
      case 'monthly':
        const inicioMes = new Date(dataBase.getFullYear(), dataBase.getMonth(), 1);
        dataFimCalculada = new Date(dataBase.getFullYear(), dataBase.getMonth() + 1, 0);
        setDataInicio(inicioMes);
        break;
      case 'yearly':
        const inicioAno = new Date(dataBase.getFullYear(), 0, 1);
        dataFimCalculada = new Date(dataBase.getFullYear(), 11, 31);
        setDataInicio(inicioAno);
        break;
      case 'daily':
      default:
        dataFimCalculada = dataBase; 
        break;
    }
    setDataFim(dataFimCalculada);
  }, [filterType, dataInicio]);


  /**
   * Efeito 2: Converte as datas para Strings
   */
  useEffect(() => {
    setDataInicioStr(formatDateForAPI(dataInicio));
    setDataFimStr(formatDateForAPI(dataFim));
  }, [dataInicio, dataFim]); 


  /**
   * Função principal que busca os dados do backend.
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
   */
  useEffect(() => {
    fetchDashboardData();
  }, [dataInicioStr, dataFimStr, syncTrigger]);
  
  // --- FUNÇÕES DE CONTROLE DO MODAL ---

  const handleAddTransactionClick = () => {
    setEditingTransaction(null);
    setIsModalOpen(true);
  };

  const handleEditClick = (transaction) => {
    setEditingTransaction(transaction);
    setIsModalOpen(true);
  };

  /**
   * REVERSÃO (A MUDANÇA ESTÁ AQUI)
   * Chamado quando o modal é salvo.
   * Agora aceita 'novosDadosDoDashboard' da API.
   */
  const handleSaveSuccess = (novosDadosDoDashboard) => {
    setIsModalOpen(false); 
    setEditingTransaction(null);
    
    // ATUALIZAÇÃO SÍNCRONA:
    // Em vez de forçar um 'fetch', nós usamos os dados
    // que o backend (lentamente) já calculou e nos enviou.
    setData(novosDadosDoDashboard); 
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingTransaction(null);
  };


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
          handleEditClick
        }} />
      </main>

      <Navbar onAddTransaction={handleAddTransactionClick} />

      {/* MUDANÇA: Passa as datas do filtro para o Modal */}
      {isModalOpen && (
        <TransactionModal 
          onClose={handleCloseModal}
          onSaveSuccess={handleSaveSuccess}
          transactionToEdit={editingTransaction}
          dataInicioStr={dataInicioStr} // <-- NOVO PROP
          dataFimStr={dataFimStr}     // <-- NOVO PROP
        />
      )}
    </div>
  );
}

export default MainLayout;