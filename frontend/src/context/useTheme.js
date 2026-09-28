// Arquivo: frontend/src/context/useTheme.js
/**
 * @file Contexto e Hook de Tema.
 * @description Separado do provedor pelo mesmo motivo de `useAuth.js`.
 */

import { createContext, useContext } from 'react';

/** Contexto com o tema atual e a função de alternância. */
export const ThemeContext = createContext(null);

/**
 * Acessa o contexto de tema.
 *
 * @returns {object} O tema atual e a função de alternância.
 */
export const useTheme = () => useContext(ThemeContext);
