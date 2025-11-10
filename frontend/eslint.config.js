// Arquivo: frontend/eslint.config.js
/*
 * Arquivo de Configuração do ESLint (O "Inspetor de Qualidade").
 *
 * Este arquivo define as regras de "linting" (análise de código)
 * para garantir a qualidade e prevenir bugs comuns no
 * JavaScript e no React.
 *
 * Ele usa o novo formato "Flat Config" do ESLint.
 */

import js from '@eslint/js'; // Regras básicas do JavaScript
import globals from 'globals'; // Define variáveis globais (ex: 'window', 'document')
import reactHooks from 'eslint-plugin-react-hooks'; // Plugin que fiscaliza as "Regras dos Hooks"
import reactRefresh from 'eslint-plugin-react-refresh'; // Plugin que garante o "Fast Refresh" do Vite

// (Funções do próprio ESLint, caso sejam necessárias)
// import { defineConfig, globalIgnores } from 'eslint/config';

export default [ // O formato "Flat Config" é um array de configurações
  
  // Ignora globalmente a pasta 'dist' (a pasta de produção compilada)
  {
    ignores: ['dist/']
  },
  
  // --- Configuração Principal (para arquivos .js e .jsx) ---
  {
    // 1. QUAIS ARQUIVOS VERIFICAR:
    // Aplica as regras abaixo em todos os arquivos .js e .jsx
    files: ['**/*.{js,jsx}'],
    
    // 2. CONFIGURAÇÃO DO "IDIOMA" (JavaScript):
    languageOptions: {
      ecmaVersion: 2020, // Entende JavaScript moderno
      sourceType: 'module', // Entende 'import' e 'export'
      globals: {
        ...globals.browser, // Reconhece 'window', 'document', 'localStorage', etc.
      },
      
      // Configura o "Parser" (o tradutor) para entender JSX
      parserOptions: {
        ecmaFeatures: { jsx: true }, // ENTENDE a sintaxe <JSX /> do React
      },
    },
    
    // 3. QUAIS CONJUNTOS DE REGRAS USAR:
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    
    rules: {
      // Carrega as regras recomendadas do ESLint (ex: "não use 'var'")
      ...js.configs.recommended.rules,
      
      // Carrega as regras CRUCIAIS do React (A "Regra de Ouro")
      // Impede bugs como:
      // - Chamar 'useState' dentro de um 'if'.
      // - Esquecer de listar uma dependência no 'useEffect'.
      ...reactHooks.configs.recommended.rules,
      
      // 4. REGRAS CUSTOMIZADAS (Nossos ajustes finos):
      
      // Garante que nosso código esteja formatado para o Fast Refresh do Vite.
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      
      // Regra padrão do ESLint: 'no-unused-vars' (Avise sobre variáveis não usadas)
      // Nossa customização: Dê erro, MAS ignore variáveis que
      // começam com _ (ex: _props, _event).
      'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      
      // Regra do React: Avise se 'props' não forem validadas
      // (Desligamos por enquanto, pois não estamos usando 'PropTypes')
      'react/prop-types': 'off',
    },
  },
];