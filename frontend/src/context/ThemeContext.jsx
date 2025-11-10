// Arquivo: frontend/src/context/ThemeContext.jsx
"""
Provedor de Contexto de Tema (O "Interruptor" Light/Dark).

Este componente gerencia o estado do tema (Claro ou Escuro)
para toda a aplicação.

Responsabilidades:
1. Ler a preferência de tema salva do 'localStorage' na inicialização.
2. Armazenar o estado atual ('light' ou 'dark').
3. Fornecer a função 'toggleTheme()' para o 'Settings.jsx' (o interruptor).
4. Aplicar/remover a classe '.light-mode' ou '.dark-mode'
   diretamente no 'document.body' do HTML, o que ativa as
   variáveis CSS corretas do 'index.css'.
"""

import React, { createContext, useState, useContext, useEffect } from 'react';

// 1. Cria o "Contexto"
const ThemeContext = createContext();

// 2. Cria o "Provedor"
export const ThemeProvider = ({ children }) => {
  
  /**
   * Função de inicialização do 'useState'.
   * É executada apenas uma vez na inicialização do app.
   * Tenta ler o 'localStorage' primeiro; se falhar,
   * define 'dark' (Azul Guardião) como o padrão.
   */
  const getInitialTheme = () => {
    return localStorage.getItem('theme') || 'dark';
  };

  const [theme, setTheme] = useState(getInitialTheme);

  /**
   * Efeito [theme]: O "Efeito Colateral" de Mudar o Tema.
   *
   * Roda sempre que o estado 'theme' mudar (seja na
   * inicialização ou no 'toggleTheme').
   */
  useEffect(() => {
    const body = document.body;
    
    // Limpa a classe antiga
    body.className = ''; 
    
    // Adiciona a classe nova (ex: 'light-mode' ou 'dark-mode')
    body.classList.add(`${theme}-mode`);
    
    // Salva a escolha do usuário para a próxima visita
    localStorage.setItem('theme', theme);
    
  }, [theme]); // <-- O gatilho é a mudança de 'theme'

  /**
   * A função que o interruptor (em 'Settings.jsx') chama.
   * Alterna o estado entre 'light' e 'dark'.
   */
  const toggleTheme = () => {
    setTheme((prevTheme) => (prevTheme === 'light' ? 'dark' : 'light'));
  };

  // 3. Compartilha o estado atual e a função de troca
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

// 4. O Hook Customizado (O "Atalho")
export const useTheme = () => {
  return useContext(ThemeContext);
};