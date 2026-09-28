// Arquivo: frontend/src/context/useAuth.js
/**
 * @file Contexto e Hook de Autenticação.
 * @description O objeto de contexto e o hook vivem aqui para que o arquivo do
 * provedor exporte apenas componentes — condição para o Fast Refresh do Vite
 * preservar o estado ao editar.
 */

import { createContext, useContext } from 'react';

/** Contexto com o estado e as ações de autenticação. */
export const AuthContext = createContext(null);

/**
 * Acessa o contexto de autenticação.
 *
 * @returns {object} Estado e ações de autenticação.
 */
export const useAuth = () => useContext(AuthContext);
