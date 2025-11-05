// Arquivo: frontend/src/context/ThemeContext.jsx
// Responsabilidade: O "Cérebro" que controla o Modo Claro/Escuro.

import React, { createContext, useState, useContext, useEffect } from 'react';

const ThemeContext = createContext();

export const ThemeProvider = ({ children }) => {
  // 1. Tenta pegar o tema salvo; se não houver, usa 'dark' (Azul Guardião) como padrão.
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');

  // 2. O "Efeito Colateral":
  //    Toda vez que o estado 'theme' mudar...
  useEffect(() => {
    // ...aplica a classe 'light-mode' ou 'dark-mode' no <body> do HTML
    document.body.className = ''; // Limpa classes antigas
    document.body.classList.add(`${theme}-mode`);
    // ...e salva a escolha no localStorage
    localStorage.setItem('theme', theme);
  }, [theme]); // Roda toda vez que 'theme' mudar

  // 3. A função que o "interruptor" vai chamar
  const toggleTheme = () => {
    setTheme((prevTheme) => (prevTheme === 'light' ? 'dark' : 'light'));
  };

  // 4. Compartilha o tema atual e a função de troca
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

// 5. O "Hook" customizado para facilitar o
export const useTheme = () => {
  return useContext(ThemeContext);
};