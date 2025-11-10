// Arquivo: frontend/src/components/FilterControls/FilterControls.jsx
"""
Componente Reutilizável de Controles de Filtro (V3.9).

Este componente renderiza a UI completa dos filtros de data:
1. Os botões de período (Diário, Semanal, Mensal, Anual).
2. O botão "Personalizado".
3. O(s) calendário(s) ('<input type="date">').

Este é um "Componente Controlado" (Controlled Component).
Ele não tem estado próprio. Ele recebe o estado atual
(ex: 'filterType', 'dataInicio') e as funções de 'setter'
(ex: 'setFilterType', 'setDataInicio') diretamente do "Pai"
(o 'MainLayout.jsx', através do 'Outlet').
"""

import React from 'react';
import './FilterControls.css';

// --- Funções Auxiliares (Helpers) de Data ---

/**
 * Lida com a mudança do calendário.
 * Converte a string 'AAAA-MM-DD' (do input) para um
 * objeto Date() no fuso horário local correto,
 * prevenindo o "bug do dia anterior" (fuso UTC).
 */
const handleDateChange = (event, setDate) => {
  const dateString = event.target.value;
  // O input 'date' (mesmo local) retorna AAAA-MM-DD
  // Precisamos tratar o fuso horário para não pular um dia
  const data = new Date(dateString);
  const dataLocal = new Date(data.valueOf() + data.getTimezoneOffset() * 60000);
  setDate(dataLocal);
};

/**
 * Formata um objeto Date() de volta para a string "AAAA-MM-DD"
 * que o '<input type="date">' exige como valor.
 */
const formatISODate = (dateObject) => {
  const date = new Date(dateObject); 
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  return `${year}-${month}-${day}`;
};
// ---------------------------------------------------


// --- O COMPONENTE ---
function FilterControls({ 
  filterType, 
  setFilterType, 
  dataInicio,
  setDataInicio,
  dataFim,
  setDataFim
}) {
  
  // Define o 'max' (hoje) para os calendários
  const maxDateForPicker = formatISODate(new Date());

  /**
   * Lógica de 'onClick' dos botões (V3.9).
   * Esta é a lógica "inteligente" que impede o loop infinito
   * (o bug 'Maximum update depth').
   *
   * Ela define o tipo de filtro E a data de início
   * correta para aquele filtro, tudo de uma vez.
   */
  const handleFilterChange = (newFilterType) => {
    // Usa HOJE como base para filtros relativos
    const dataBase = new Date(); 
    let novaDataInicio;

    switch (newFilterType) {
      case 'weekly':
        // Calcula o primeiro dia (Segunda) da semana atual
        const diaDaSemana = dataBase.getDay();
        const diff = dataBase.getDate() - diaDaSemana + (diaDaSemana === 0 ? -6 : 1);
        novaDataInicio = new Date(dataBase.setDate(diff));
        break;
      case 'monthly':
        // Primeiro dia do mês atual
        novaDataInicio = new Date(dataBase.getFullYear(), dataBase.getMonth(), 1);
        break;
      case 'yearly':
        // Primeiro dia do ano atual
        novaDataInicio = new Date(dataBase.getFullYear(), 0, 1);
        break;
      case 'personalizado':
        // Não reseta a data, mantém a seleção atual
        novaDataInicio = dataInicio; 
        break;
      case 'daily':
      default:
        novaDataInicio = dataBase; // Reseta para hoje
        break;
    }
    
    // Define os dois estados no "Pai" (MainLayout) de uma vez
    setFilterType(newFilterType);
    setDataInicio(novaDataInicio);
  };


  return (
    <div className="filter-tabs-container">
      {/* Botões de Filtro */}
      <div className="filter-tabs">
        <button 
          className={`tab-button ${filterType === 'daily' ? 'active' : ''}`}
          onClick={() => handleFilterChange('daily')}
        >
          Diário
        </button>
        <button 
          className={`tab-button ${filterType === 'weekly' ? 'active' : ''}`}
          onClick={() => handleFilterChange('weekly')}
        >
          Semanal
        </button>
        <button 
          className={`tab-button ${filterType === 'monthly' ? 'active' : ''}`}
          onClick={() => handleFilterChange('monthly')}
        >
          Mensal
        </button>
        <button 
          className={`tab-button ${filterType === 'yearly' ? 'active' : ''}`}
          onClick={() => handleFilterChange('yearly')}
        >
          Anual
        </button>
        <button 
          className={`tab-button ${filterType === 'personalizado' ? 'active' : ''}`}
          onClick={() => handleFilterChange('personalizado')}
        >
          Personalizado
        </button>
      </div>
      
      {/* O Calendário (Renderização Condicional V3.8) */}
      <div className="date-picker-container">
        {filterType === 'personalizado' ? (
          // 1. MODO PERSONALIZADO (Dois calendários)
          <div className="date-range-wrapper">
            <input
              type="date"
              className="date-picker-input"
              value={formatISODate(dataInicio)}
              onChange={(e) => handleDateChange(e, setDataInicio)}
              max={maxDateForPicker}
            />
            <span>até</span>
            <input
              type="date"
              className="date-picker-input"
              value={formatISODate(dataFim)}
              onChange={(e) => handleDateChange(e, setDataFim)}
              max={maxDateForPicker}
            />
          </div>
        ) : (
          // 2. MODO NORMAL (Um calendário)
          // (Controla 'dataInicio', e o Pai 'MainLayout' calcula 'dataFim')
          <input
            type="date"
            className="date-picker-input"
            value={formatISODate(dataInicio)}
            onChange={(e) => handleDateChange(e, setDataInicio)}
            max={maxDateForPicker}
          />
        )}
      </div>
    </div>
  );
}

export default FilterControls;