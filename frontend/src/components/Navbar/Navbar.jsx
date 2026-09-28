// Arquivo: frontend/src/components/Navbar/Navbar.jsx
/**
 * @file Barra de Navegação.
 * @description Navegação principal em uma única linha no topo.
 */

import { IoAdd, IoMoonOutline, IoSunnyOutline } from 'react-icons/io5';
import { NavLink } from 'react-router-dom';

import logo from '../../assets/logo.png';
import { useTheme } from '../../context/useTheme';
import './Navbar.css';

/** Itens de navegação, na ordem em que aparecem. */
const LINKS = [
  { para: '/', rotulo: 'Painel', exato: true },
  { para: '/reports', rotulo: 'Relatórios' },
  { para: '/settings', rotulo: 'Ajustes' },
  { para: '/profile', rotulo: 'Perfil' },
];

/**
 * Barra de navegação superior.
 *
 * @param {object} props - Propriedades do componente.
 * @param {function} props.onAddTransaction - Abre o modal de nova transação.
 * @returns {JSX.Element} A barra de navegação.
 */
function Navbar({ onAddTransaction }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <nav className="navbar">
      <div className="navbar-conteudo">
        <NavLink to="/" className="navbar-marca">
          <img src={logo} alt="" />
          NOMAD
        </NavLink>

        <div className="navbar-links">
          {LINKS.map(({ para, rotulo, exato }) => (
            <NavLink
              key={para}
              to={para}
              end={exato}
              className={({ isActive }) =>
                isActive ? 'navbar-link ativo' : 'navbar-link'
              }
            >
              <span>{rotulo}</span>
            </NavLink>
          ))}

          <div className="navbar-acoes">
            <button
              type="button"
              className="botao-discreto"
              onClick={toggleTheme}
              aria-label={
                theme === 'dark' ? 'Usar tema claro' : 'Usar tema escuro'
              }
            >
              {theme === 'dark' ? (
                <IoSunnyOutline size={18} />
              ) : (
                <IoMoonOutline size={18} />
              )}
            </button>

            <button
              type="button"
              className="botao botao-primario"
              onClick={onAddTransaction}
            >
              <IoAdd size={18} />
              <span>Novo</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
