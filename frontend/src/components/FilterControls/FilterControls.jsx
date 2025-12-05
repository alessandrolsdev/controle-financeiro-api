// Arquivo: frontend/src/components/FilterControls/FilterControls.jsx
/**
 * @file Controles de Filtro de Data.
 * @description Componente para seleção de intervalos de data (Diário, Semanal, Mensal, Anual, Personalizado).
 */

import React from 'react';
import './FilterControls.css';

/**
 * Manipula a alteração de data no input.
 * Converte a string do input (AAAA-MM-DD) para um objeto Date ajustado ao fuso horário local.
 *
 * @param {Event} event - O evento de mudança do input.
 * @param {function} setDate - Função setter para atualizar o estado da data.
 */
const handleDateChange = (event, setDate) => {
  const dateString = event.target.value;
  const data = new Date(dateString);
  const dataLocal = new Date(data.valueOf() + data.getTimezoneOffset() * 60000);
  setDate(dataLocal);
};

/**
 * Formata um objeto Date para string no formato 'AAAA-MM-DD'.
 *
 * @param {Date} dateObject - O objeto de data a ser formatado.
 * @returns {string} A data formatada.
 */
const formatISODate = (dateObject) => {
  const date = new Date(dateObject); 
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  return `${year}-${month}-${day}`;
};


/**
 * Componente de Controles de Filtro.
 *
 * Exibe botões para selecionar tipos de intervalo e inputs de data correspondentes.
 * É um componente controlado, recebendo estados e setters do componente pai.
 *
 * @param {object} props - Propriedades do componente.
 * @param {string} props.filterType - O tipo de filtro selecionado ('daily', 'weekly', 'monthly', 'yearly', 'personalizado').
 * @param {function} props.setFilterType - Função para atualizar o tipo de filtro.
 * @param {Date} props.dataInicio - Data de início do intervalo.
 * @param {function} props.setDataInicio - Função para atualizar a data de início.
 * @param {Date} props.dataFim - Data de fim do intervalo.
 * @param {function} props.setDataFim - Função para atualizar a data de fim.
 * @returns {JSX.Element} O componente renderizado.
 */
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
   * Manipula a mudança do tipo de filtro.
   * Calcula a nova data de início baseada no filtro selecionado para evitar inconsistências.
   *
   * @param {string} newFilterType - O novo tipo de filtro selecionado.
   */
  const handleFilterChange = (newFilterType) => {
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
        novaDataInicio = dataBase; 
        break;
      case 'daily':
      default:
        novaDataInicio = dataBase;
        break;
    }
    
    setFilterType(newFilterType);
    setDataInicio(novaDataInicio);
  };


  return (
    <div className="filter-tabs-container">
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
      
      <div className="date-picker-container">
        {filterType === 'personalizado' ? (
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
