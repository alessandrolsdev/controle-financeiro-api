// Arquivo: frontend/src/layouts/MainLayout.jsx
/*
 * Layout Principal (O "Pai Orquestrador").
 *
 * Este é o componente "Pai" de todas as páginas protegidas.
 * Ele é renderizado pela Rota Pai ('/') no 'App.jsx'.
 * Sua função é renderizar a 'Navbar' e o 'TransactionModal',
 * e atuar como o "cérebro" para os filtros de dados e
 * o estado do modal.
 *
 * Arquitetura de Fluxo de Dados (Pai -> Filho):
 * 1. 'MainLayout' (Pai) busca os dados do 'GET /dashboard/'.
 * 2. 'MainLayout' (Pai) gerencia os filtros de data (ex: 'Mensal').
 * 3. 'MainLayout' (Pai) passa os dados e os filtros para o
 * 'Outlet' (Filho) via 'useOutletContext'.
 * 4. 'Dashboard.jsx' e 'Reports.jsx' (Filhos) recebem e
 * renderizam esses dados.
 *
 * Arquitetura Síncrona (Deploy Gratuito):
 * Este layout usa a lógica SÍNCRONA. Quando o modal é salvo
 * (handleSaveSuccess), ele espera a resposta da API (que contém
 * os dados do dashboard recalculados) e atualiza o estado 'data'
 * instantaneamente, sem uma segunda chamada 'fetch'.
 */

import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from '../components/Navbar/Navbar';
import TransactionModal from '../components/TransactionModal/TransactionModal';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

/**
 * Função auxiliar para formatar um objeto Date() para a
 * string 'AAAA-MM-DD' que a API espera.
 */
const formatDateForAPI = (date) => {
  const dateObj = new Date(date);
  const year = dateObj.getFullYear();
  const month = (dateObj.getMonth() + 1).toString().padStart(2, '0');
  const day = dateObj.getDate().toString().padStart(2, '0');
  return `${year}-${month}-${day}`;
};

function MainLayout() {
  // --- Estados de Dados do Dashboard ---
  const [data, setData] = useState(null); // Os dados (Receitas, Gastos, etc.)
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // --- Estados do Cérebro de Autenticação (V7.6) ---
  const { syncTrigger, isAuthLoading } = useAuth(); 

  // --- Estados do Filtro Global (V3.8) ---
  const [filterType, setFilterType] = useState('daily');
  const [dataInicio, setDataInicio] = useState(new Date());
  const [dataFim, setDataFim] = useState(new Date());       
  
  // O 'estado derivado' (strings) que é enviado para a API
  const [dataInicioStr, setDataInicioStr] = useState('');
  const [dataFimStr, setDataFimStr] = useState('');

  // --- Estados do Modal (V6.0) ---
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState(null); // (null = Criar, Objeto = Editar)

  /**
   * Efeito 1: Calcula o 'dataFim' (Corrigido V9.1)
   *
   * Ouve o 'filterType' e 'dataInicio' (controlados pelo FilterControls).
   * Se o filtro NÃO for 'personalizado', ele calcula e define o 'dataFim'.
   * Esta lógica impede o loop infinito de 'Maximum update depth'.
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
   * Efeito 2: Converte os objetos Date() em Strings
   * (Usado para a API)
   */
  useEffect(() => {
    setDataInicioStr(formatDateForAPI(dataInicio));
    setDataFimStr(formatDateForAPI(dataFim));
  }, [dataInicio, dataFim]); 


  /**
   * Função principal que busca os dados do 'GET /dashboard/'.
   */
  const fetchDashboardData = async () => {
    // Não busca se as datas ainda não foram calculadas
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
   * Efeito 3: Busca os dados (Corrigido V7.6)
   *
   * Ouve as datas (convertidas em string) E
   * o 'syncTrigger' (da fila offline) E
   * o 'isAuthLoading' (da autenticação).
   */
  useEffect(() => {
    // Impede a "race condition" (corrida de dados):
    // Só busca dados APÓS o AuthContext (Pai)
    // ter confirmado que a autenticação está pronta.
    if (!dataInicioStr || !dataFimStr || isAuthLoading) return;
    
    fetchDashboardData();
  }, [dataInicioStr, dataFimStr, syncTrigger, isAuthLoading]); // <-- Ouve todos os gatilhos
  
  // --- FUNÇÕES DE CONTROLE DO MODAL ---

  /** (V6.0) Chamado pelo botão '+' da Navbar (Modo de Criação) */
  const handleAddTransactionClick = () => {
    setEditingTransaction(null);
    setIsModalOpen(true);
  };

  /** (V6.0) Chamado pelo botão 'Editar' no Dashboard.jsx */
  const handleEditClick = (transaction) => {
    setEditingTransaction(transaction);
    setIsModalOpen(true);
  };

  /**
   * (V-Revert Síncrona)
   * Chamado quando o modal (Criar/Editar) é salvo.
   * Recebe os dados do dashboard atualizados diretamente da API.
   */
  const handleSaveSuccess = (novosDadosDoDashboard) => {
    setIsModalOpen(false); 
    setEditingTransaction(null);
    setData(novosDadosDoDashboard); // Atualiza a UI instantaneamente
  };
  
  /**
   * (V9.0) Chamado pelo Dashboard.jsx quando o 'api.delete'
   * síncrono retorna os dados atualizados.
   */
  const handleDeleteSuccess = (novosDadosDoDashboard) => {
    setData(novosDadosDoDashboard);
  };

  /** (V6.0) Garante que o estado de edição seja limpo ao fechar */
  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingTransaction(null);
  };

  // (V7.6) Tela de carregamento global
  // Impede que as páginas 'filhas' sejam renderizadas
  // antes que a autenticação esteja pronta.
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
        {/*
          O <Outlet /> renderiza o componente "filho" (Dashboard ou Reports).
          'context={...}' é a "injeção de dependência" do React Router.
          Todos os dados e funções aqui são passados para o filho,
          que os acessa via 'useOutletContext()'.
        */}
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

      {/* A Navbar fica fixa no rodapé */}
      <Navbar onAddTransaction={handleAddTransactionClick} />

      {/* O Modal (controlado 100% pelo 'MainLayout') */}
      {isModalOpen && (
        <TransactionModal 
          onClose={handleCloseModal}
          onSaveSuccess={handleSaveSuccess}
          transactionToEdit={editingTransaction} // (null = Criar, Objeto = Editar)
          dataInicioStr={dataInicioStr} // (Para o recálculo síncrono)
          dataFimStr={dataFimStr}     // (Para o recálculo síncrono)
        />
      )}
    </div>
  );
}

export default MainLayout;