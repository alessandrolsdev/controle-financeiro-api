// Arquivo: frontend/src/components/FilterControls/FilterControls.jsx
// (VERSÃO V3.9 - CORREÇÃO DO LOOP INFINITO)
/*
REATORAÇÃO (Missão V3.9 - A CORREÇÃO):
1. A lógica de "resetar" a data de início foi MOVIDA
   para DENTRO dos 'onClick' dos botões.
2. O 'onClick' de "Mensal", por exemplo, agora chama
   'handleFilterChange' que define o 'filterType' E
   o 'dataInicio' (para o 1º dia do mês) ao mesmo tempo.
3. Isso impede que o 'MainLayout' entre em um loop infinito.
*/

import React from 'react';
import './FilterControls.css';

// --- FUNÇÕES AUXILIARES (para os inputs de data) ---
const handleDateChange = (event, setDate) => {
  const dateString = event.target.value;
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
   * 1. A NOVA LÓGICA DE 'onClick'
   * Esta função agora é o "cérebro".
   * Ela define o tipo de filtro E a data de início
   * correta para aquele filtro, tudo de uma vez.
   */
  const handleFilterChange = (newFilterType) => {
    const dataBase = new Date(); // Usa HOJE como base para resetar
    
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
        // No modo personalizado, não resetamos, usamos a data atual
        novaDataInicio = dataInicio; 
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
      {/* 2. Botões de Filtro (agora usam 'handleFilterChange') */}
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
      
      {/* 3. O Calendário (agora 100% correto) */}
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