// Arquivo: frontend/src/components/FilterControls/FilterControls.jsx
/**
 * @file Controles de Filtro de Data.
 * @description Componente para seleção de intervalos de data (Diário, Semanal, Mensal, Anual, Personalizado).
 */

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
      case 'weekly': {
        // O bloco isola as declarações: sem ele, `const` dentro de um `case`
        // vaza para os outros ramos do switch e pode ser lido antes da
        // inicialização.
        const diaDaSemana = dataBase.getDay();
        const diff =
          dataBase.getDate() - diaDaSemana + (diaDaSemana === 0 ? -6 : 1);
        novaDataInicio = new Date(dataBase.setDate(diff));
        break;
      }
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

  /** Opções de período, na ordem em que aparecem. */
  const OPCOES = [
    { valor: 'daily', rotulo: 'Dia' },
    { valor: 'weekly', rotulo: 'Semana' },
    { valor: 'monthly', rotulo: 'Mês' },
    { valor: 'yearly', rotulo: 'Ano' },
    { valor: 'personalizado', rotulo: 'Período' },
  ];

  return (
    <div className="filtros">
      <div className="filtros-periodo" role="group" aria-label="Período">
        {OPCOES.map(({ valor, rotulo }) => (
          <button
            key={valor}
            type="button"
            className={
              filterType === valor ? 'filtro-opcao ativo' : 'filtro-opcao'
            }
            aria-pressed={filterType === valor}
            onClick={() => handleFilterChange(valor)}
          >
            {rotulo}
          </button>
        ))}
      </div>

      <div className="filtros-datas">
        <input
          type="date"
          value={formatISODate(dataInicio)}
          onChange={(e) => handleDateChange(e, setDataInicio)}
          max={maxDateForPicker}
          aria-label="Data inicial"
        />

        {filterType === 'personalizado' && (
          <>
            <span className="filtros-separador">até</span>
            <input
              type="date"
              value={formatISODate(dataFim)}
              onChange={(e) => handleDateChange(e, setDataFim)}
              max={maxDateForPicker}
              aria-label="Data final"
            />
          </>
        )}
      </div>
    </div>
  );
}

export default FilterControls;
