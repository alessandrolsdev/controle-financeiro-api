// Arquivo: frontend/eslint.config.js
/**
 * @file Configuração do ESLint (Flat Config).
 * @description Regras de qualidade para JavaScript e React.
 *
 * Correção da issue #10: a configuração anterior não carregava o
 * `eslint-plugin-react`, então a regra `jsx-uses-vars` não existia e o ESLint
 * não enxergava o uso de um componente dentro do JSX. O resultado eram dezenas
 * de falsos "defined but never used" para componentes que estavam sendo usados
 * normalmente — ruído que escondia os poucos imports realmente órfãos.
 *
 * Os arquivos de configuração do próprio build rodam em Node, não no
 * navegador, e por isso recebem um bloco próprio com os globais corretos.
 */

import js from '@eslint/js';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import globals from 'globals';

export default [
  {
    ignores: ['dist/', 'dev-dist/', 'node_modules/'],
  },

  // --- Código da aplicação (roda no navegador) ---
  {
    files: ['src/**/*.{js,jsx}'],

    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.browser,
      },
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },

    plugins: {
      react,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },

    settings: {
      react: { version: 'detect' },
    },

    rules: {
      ...js.configs.recommended.rules,

      // Marca como "usado" todo identificador referenciado em JSX. É esta
      // regra que faltava e causava os falsos positivos da issue #10.
      'react/jsx-uses-vars': 'error',
      'react/jsx-uses-react': 'off', // desnecessário com o JSX transform novo
      'react/react-in-jsx-scope': 'off',
      'react/prop-types': 'off',

      ...reactHooks.configs.recommended.rules,

      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],

      'no-unused-vars': [
        'error',
        {
          // Permite descartar valores explicitamente com o prefixo `_`,
          // padrão comum em desestruturação.
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],

      // Erros silenciosos que o `js.configs.recommended` deixa como aviso.
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      eqeqeq: ['error', 'smart'],
    },
  },

  // --- Arquivos de configuração e build (rodam em Node) ---
  {
    files: ['*.config.js', 'vite.config.js', 'eslint.config.js'],

    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.node,
      },
    },

    rules: {
      ...js.configs.recommended.rules,
      'no-unused-vars': 'error',
    },
  },

  // --- Service worker gerado e scripts utilitários ---
  {
    files: ['public/**/*.js'],
    languageOptions: {
      globals: {
        ...globals.serviceworker,
        ...globals.browser,
      },
    },
  },
];
