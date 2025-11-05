// Arquivo: frontend/src/components/Navbar/Navbar.jsx
// Responsabilidade: A barra de navegação inferior principal do app.

import React from 'react';
import { NavLink } from 'react-router-dom';
import './Navbar.css';

// Importa os ícones que vamos usar (baseado nos mockups)
// Usaremos os ícones "Io" (Ionicons) que são limpos e modernos
import { IoHomeOutline, IoPieChartOutline, IoSettingsOutline, IoPersonOutline, IoAdd } from 'react-icons/io5';

/**
 * Componente da Barra de Navegação Inferior (mobile-first).
 * @param {object} props
 * @param {function} props.onAddTransaction - Função de callback para abrir o modal
 */
function Navbar({ onAddTransaction }) {
  
  // Esta função de 'classe ativa' é o que faz o ícone mudar de cor
  // O NavLink nos dá um 'isActive' booleano.
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
        
        {/* Link 2: Relatórios (Placeholder futuro) */}
        <NavLink to="/reports" className={getNavLinkClass}>
          <IoPieChartOutline size={24} />
          <span>Relatórios</span>
        </NavLink>
        
        {/* Link 3: O Botão de Adicionar (FAB) no meio */}
        <div className="nav-fab-container">
          {/* Este não é um <Link>, é um <button> que chama a função de abrir o modal */}
          <button className="nav-fab" onClick={onAddTransaction}>
            <IoAdd size={32} />
          </button>
        </div>
        
        {/* Link 4: Ajustes (Configurações) */}
        <NavLink to="/settings" className={getNavLinkClass}>
          <IoSettingsOutline size={24} />
          <span>Ajustes</span>
        </NavLink>
        
        {/* Link 5: Perfil (Placeholder futuro) */}
        <NavLink to="/profile" className={getNavLinkClass}>
          <IoPersonOutline size={24} />
          <span>Perfil</span>
        </NavLink>

      </div>
    </nav>
  );
} 

export default Navbar;