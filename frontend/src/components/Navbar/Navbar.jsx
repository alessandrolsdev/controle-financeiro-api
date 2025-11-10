// Arquivo: frontend/src/components/Navbar/Navbar.jsx
/*
 * Componente da Barra de Navegação Inferior (Navbar).
 *
 * Este componente renderiza a barra de navegação principal (fixa
 * no rodapé) da aplicação, com o design "mobile-first".
 *
 * Responsabilidades:
 * 1. Renderizar os links de navegação (<NavLink>) para as
 * páginas principais (Início, Relatórios, Ajustes, Perfil).
 * 2. Indicar visualmente qual link está 'ativo' (usando 'getNavLinkClass').
 * 3. Renderizar o Botão de Ação Flutuante (FAB - o '+').
 * 4. Delegar o 'onClick' do FAB para o 'MainLayout' (Pai)
 * através da prop 'onAddTransaction'.
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import './Navbar.css';

// Importa os ícones 'Ionicons' (Io) que usamos
import { 
  IoHomeOutline, 
  IoPieChartOutline, 
  IoSettingsOutline, 
  IoPersonOutline, 
  IoAdd 
} from 'react-icons/io5';

/**
 * Renderiza a barra de navegação inferior.
 *
 * @param {object} props
 * @param {function} props.onAddTransaction - Função de callback (do MainLayout)
 * para abrir o modal de transação.
 */
function Navbar({ onAddTransaction }) {
  
  /**
   * Função helper para o 'react-router-dom'.
   * O 'NavLink' nos passa um objeto '{ isActive: boolean }'.
   * Nós o usamos para retornar a classe CSS correta.
   */
  const getNavLinkClass = ({ isActive }) => {
    return isActive ? 'nav-item active' : 'nav-item';
  };

  return (
    <nav className="navbar-container">
      <div className="navbar-links">
        
        {/* Link 1: Início (Dashboard) */}
        <NavLink to="/" className={getNavLinkClass}>
          <IoHomeOutline size={24} />
          <span>Início</span>
        </NavLink>
        
        {/* Link 2: Relatórios */}
        <NavLink to="/reports" className={getNavLinkClass}>
          <IoPieChartOutline size={24} />
          <span>Relatórios</span>
        </NavLink>
        
        {/* Link 3: O Botão de Adicionar (FAB) no meio */}
        <div className="nav-fab-container">
          {/* Este não é um <NavLink>, é um <button>
            que chama a função do Pai para abrir o modal.
          */}
          <button className="nav-fab" onClick={onAddTransaction} aria-label="Adicionar nova transação">
            <IoAdd size={32} />
          </button>
        </div>
        
        {/* Link 4: Ajustes (Configurações) */}
        <NavLink to="/settings" className={getNavLinkClass}>
          <IoSettingsOutline size={24} />
          <span>Ajustes</span>
        </NavLink>
        
        {/* Link 5: Perfil */}
        <NavLink to="/profile" className={getNavLinkClass}>
          <IoPersonOutline size={24} />
          <span>Perfil</span>
        </NavLink>

      </div>
    </nav>
  );
} 

export default Navbar;