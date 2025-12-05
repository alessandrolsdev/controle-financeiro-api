// Arquivo: frontend/src/components/Navbar/Navbar.jsx
/**
 * @file Barra de Navegação Inferior (Navbar).
 * @description Componente de navegação principal da aplicação, contendo links e o botão de ação flutuante (FAB).
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import './Navbar.css';

import { 
  IoHomeOutline, 
  IoPieChartOutline, 
  IoSettingsOutline, 
  IoPersonOutline, 
  IoAdd 
} from 'react-icons/io5';

/**
 * Componente Navbar.
 *
 * Exibe a barra de navegação no rodapé da página.
 * Contém links para as rotas principais e um botão central para adicionar transações.
 *
 * @param {object} props - Propriedades do componente.
 * @param {function} props.onAddTransaction - Função executada ao clicar no botão de adicionar (FAB).
 * @returns {JSX.Element} A navbar renderizada.
 */
function Navbar({ onAddTransaction }) {
  
  /**
   * Determina a classe CSS para o link de navegação com base no estado ativo.
   * @param {object} navState - Estado de navegação fornecido pelo NavLink.
   * @param {boolean} navState.isActive - Indica se a rota atual corresponde ao link.
   * @returns {string} A string de classes CSS.
   */
  const getNavLinkClass = ({ isActive }) => {
    return isActive ? 'nav-item active' : 'nav-item';
  };

  return (
    <nav className="navbar-container">
      <div className="navbar-links">
        
        <NavLink to="/" className={getNavLinkClass}>
          <IoHomeOutline size={24} />
          <span>Início</span>
        </NavLink>
        
        <NavLink to="/reports" className={getNavLinkClass}>
          <IoPieChartOutline size={24} />
          <span>Relatórios</span>
        </NavLink>
        
        <div className="nav-fab-container">
          <button className="nav-fab" onClick={onAddTransaction} aria-label="Adicionar nova transação">
            <IoAdd size={32} />
          </button>
        </div>
        
        <NavLink to="/settings" className={getNavLinkClass}>
          <IoSettingsOutline size={24} />
          <span>Ajustes</span>
        </NavLink>
        
        <NavLink to="/profile" className={getNavLinkClass}>
          <IoPersonOutline size={24} />
          <span>Perfil</span>
        </NavLink>

      </div>
    </nav>
  );
} 

export default Navbar;
