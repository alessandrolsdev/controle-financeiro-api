// Arquivo: frontend/src/context/ThemeContext.jsx
/**
 * @file Contexto de Tema.
 * @description Gerencia o tema da aplicação (Claro/Escuro), persistindo a preferência do usuário e aplicando as classes CSS globais.
 */

import React, { createContext, useState, useContext, useEffect } from 'react';

/**
 * Contexto que armazena o estado do tema.
 */
const ThemeContext = createContext();

/**
 * Provedor de Tema.
 *
 * Envolve a aplicação e gerencia a alternância entre temas claro e escuro.
 * Aplica a classe correspondente ao corpo do documento HTML.
 *
 * @param {object} props - Propriedades do componente.
 * @param {React.ReactNode} props.children - Componentes filhos que terão acesso ao contexto.
 * @returns {JSX.Element} O provedor de contexto.
 */
export const ThemeProvider = ({ children }) => {
  
  /**
   * Recupera o tema inicial armazenado no localStorage ou define o padrão como 'dark'.
   * @returns {string} O tema inicial ('light' ou 'dark').
   */
  const getInitialTheme = () => {
    return localStorage.getItem('theme') || 'dark';
  };

  const [theme, setTheme] = useState(getInitialTheme);

  /**
   * Efeito colateral que aplica o tema ao documento.
   *
   * Remove classes antigas e adiciona a nova classe ('light-mode' ou 'dark-mode') ao body.
   * Persiste a escolha no localStorage.
   */
  useEffect(() => {
    const body = document.body;
    body.className = ''; 
    body.classList.add(`${theme}-mode`);
    localStorage.setItem('theme', theme);
  }, [theme]);

  /**
   * Alterna entre os temas claro e escuro.
   */
  const toggleTheme = () => {
    setTheme((prevTheme) => (prevTheme === 'light' ? 'dark' : 'light'));
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

/**
 * Hook personalizado para acessar o contexto de tema.
 *
 * @returns {object} O contexto de tema (theme, toggleTheme).
 */
export const useTheme = () => {
  return useContext(ThemeContext);
};
