// Arquivo: frontend/src/components/FilterControls/FilterControls.jsx
// (VERSÃO V9.1 - CORREÇÃO DEFINITIVA DO LOOP INFINITO)
/*
CHECK-UP (V9.1): Este arquivo contém a lógica 'handleFilterChange'
que (corretamente) chama 'setFilterType' E 'setDataInicio'
ao mesmo tempo. Esta é a correção para o bug 'Maximum update depth'.
*/

import React from 'react';
import './FilterControls.css';

// --- FUNÇÕES AUXILIARES (para os inputs de data) ---
const handleDateChange = (event, setDate) => {
  const dateString = event.target.value;
  // O input 'date' (mesmo local) retorna AAAA-MM-DD
  // Precisamos tratar o fuso horário para não pular um dia
  const data = new Date(dateString);
  const dataLocal = new Date(data.valueOf() + data.getTimezoneOffset() * 60000);
  setDate(dataLocal);
};

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
  
  const maxDateForPicker = formatISODate(new Date());

  /**
   * 1. A LÓGICA DE 'onClick' (V3.9)
   * Esta função é o "cérebro" que impede o loop infinito.
   * Ela define o tipo de filtro E a data de início
   * correta para aquele filtro, tudo de uma vez.
   */
  const handleFilterChange = (newFilterType) => {
    // Usa HOJE como base para 'Diário'
    // Usa a data ATUAL do filtro para 'Personalizado'
    const dataBase = (newFilterType === 'personalizado') ? new Date(dataInicio) : new Date();
    
    let novaDataInicio;

    switch (newFilterType) {
      case 'weekly':
        const diaDaSemana = dataBase.getDay();
        const diff = dataBase.getDate() - diaDaSemana + (diaDaSemana === 0 ? -6 : 1);
        novaDataInicio = new Date(dataBase.setDate(diff));
        break;
      case 'monthly':
        novaDataInicio = new Date(dataBase.getFullYear(), dataBase.getMonth(), 1);
        break;
      case 'yearly':
        novaDataInicio = new Date(dataBase.getFullYear(), 0, 1);
        break;
      case 'personalizado':
        novaDataInicio = dataBase; // Mantém a data de início atual
        break;
      case 'daily':
      default:
        novaDataInicio = dataBase; // Reseta para hoje
        break;
    }
    
    // Define os dois estados no Pai (MainLayout) de uma vez
    setFilterType(newFilterType);
    setDataInicio(novaDataInicio);
  };


  return (
    <div className="filter-tabs-container">
      {/* 2. Botões de Filtro (usam 'handleFilterChange') */}
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
      
      {/* 3. O Calendário (Renderização Condicional V3.8) */}
      <div className="date-picker-container">
        {filterType === 'personalizado' ? (
          // MODO PERSONALIZADO (Dois calendários)
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
          // MODO NORMAL (Um calendário, que define o 'dataInicio')
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