// Arquivo: frontend/eslint.config.js
// Responsabilidade: Configurar o "Inspetor de Qualidade" (ESLint)
// Este arquivo define as regras que o nosso código deve seguir.

import js from '@eslint/js' // Regras básicas do JavaScript
import globals from 'globals' // Define variáveis globais (ex: 'window', 'document')
import reactHooks from 'eslint-plugin-react-hooks' // Plugin que fiscaliza as "Regras dos Hooks" do React
import reactRefresh from 'eslint-plugin-react-refresh' // Plugin que garante o "Fast Refresh" do Vite
import { defineConfig, globalIgnores } from 'eslint/config' // Funções do próprio ESLint

export default defineConfig([
  // Ignora globalmente a pasta 'dist' (a pasta de produção compilada)
  globalIgnores(['dist']),
  
  {
    // 1. QUAIS ARQUIVOS VERIFICAR:
    // Aplica as regras abaixo em todos os arquivos .js e .jsx
    files: ['**/*.{js,jsx}'],
    
    // 2. QUAIS CONJUNTOS DE REGRAS USAR:
    extends: [
      js.configs.recommended, // Regras padrão do ESLint (ex: "não use 'var'")
      
      // Regras CRUCIAIS do React.
      // Impede bugs como:
      // - Chamar 'useState' dentro de um 'if'.
      // - Esquecer de listar uma dependência no 'useEffect'.
      reactHooks.configs['recommended-latest'], 
      
      // Garante que nosso código esteja formatado para o Fast Refresh do Vite.
      reactRefresh.configs.vite,
    ],
    
    // 3. CONFIGURAÇÃO DO "IDIOMA" (JavaScript):
    languageOptions: {
      ecmaVersion: 2020, // Entende JavaScript moderno
      globals: globals.browser, // Reconhece variáveis de navegador (ex: 'window', 'localStorage')
      
      // Configura o "Parser" (o tradutor)
      parserOptions: {
        ecmaVersion: 'latest', // Entende as features mais novas (ex: 'await')
        ecmaFeatures: { jsx: true }, // ENTENDE a sintaxe JSX do React
        sourceType: 'module', // ENTENDE 'import' e 'export'
      },
    },
    
    // 4. REGRAS CUSTOMIZADAS (Onde nós ajustamos o "inspetor"):
    rules: {
      // Regra padrão do ESLint: 'no-unused-vars' (Avise sobre variáveis não usadas)
      // Nossa customização: Dê erro, MAS ignore variáveis que
      // começam com letra MAIÚSCULA ou _ (comum em React para 'props' não usadas).
      'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }],
      
      // Desativa a regra 'react-refresh/only-export-components'
      // (É uma regra comum de desativar em projetos Vite)
      'react-refresh/only-export-components': 'off',
    },
  },
])