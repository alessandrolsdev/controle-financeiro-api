// Arquivo: frontend/src/pages/Settings/Settings.jsx
/*
 * Página de Ajustes e Configurações.
 *
 * Esta página é um "Filho" do 'MainLayout'.
 * É o "Centro de Gerenciamento de Categorias" (CRUD completo)
 * e também controla as configurações do app (como o Tema).
 *
 * Responsabilidades:
 * 1. Gerenciar um formulário "modo-duplo" para Criar e Editar categorias.
 * 2. Listar, Atualizar (PUT) e Deletar (DELETE) categorias (V8.0 / V9.0).
 * 3. Gerenciar o 'toggle' (interruptor) de Tema (Light/Dark).
 */

import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import './Settings.css';
import { useTheme } from '../../context/ThemeContext';
// (V8.0) Importa os ícones de Ação
import { IoPencil, IoTrash } from 'react-icons/io5';

function Settings() {
  // --- Estados Globais ---
  const { theme, toggleTheme } = useTheme(); // Pega o estado do Tema
  
  // --- Estados Locais ---
  const [categorias, setCategorias] = useState([]);
  const [loading, setLoading] = useState(true);

  // --- Estados do Formulário ---
  const [nomeCategoria, setNomeCategoria] = useState('');
  const [tipoCategoria, setTipoCategoria] = useState('Gasto');
  const [corCategoria, setCorCategoria] = useState('#FF7A00'); // (V5.0) Cor
  
  // (V8.0) Estado que controla o "modo" do formulário
  const [editingCategoryId, setEditingCategoryId] = useState(null); // null = Criar, ID = Editar
  const isEditMode = Boolean(editingCategoryId); // True se estivermos editando

  // --- Estados de UI (Feedback) ---
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  /**
   * Busca (GET /categorias) a lista de categorias do backend.
   * Chamado na montagem do componente e após qualquer CUD.
   */
  const fetchCategorias = async () => {
    try {
      setLoading(true);
      const response = await api.get('/categorias/');
      setCategorias(response.data);
      setLoading(false);
    } catch (err) {
      console.error("Erro ao buscar categorias:", err);
      // (Define o erro no formulário principal se a lista falhar)
      setError("Não foi possível carregar as categorias.");
      setLoading(false);
    }
  };

  /**
   * Efeito [onLoad]: Busca as categorias na primeira
   * renderização do componente.
   */
  useEffect(() => {
    fetchCategorias();
  }, []); // [] = Roda apenas uma vez

  /**
   * Reseta o formulário para o estado de "Criação".
   * Limpa os campos e sai do modo de edição.
   */
  const resetForm = () => {
    setNomeCategoria('');
    setTipoCategoria('Gasto');
    setCorCategoria('#FF7A00');
    setEditingCategoryId(null);
  };
  
  // --- Funções de CRUD (V8.0) ---

  /**
   * Chamado ao clicar no ícone de lápis (Editar).
   * Preenche o formulário com os dados da categoria selecionada
   * e entra no "Modo de Edição".
   */
  const handleEditClick = (categoria) => {
    // Define os estados do formulário
    setNomeCategoria(categoria.nome);
    setTipoCategoria(categoria.tipo);
    setCorCategoria(categoria.cor);
    // Define o ID que estamos editando
    setEditingCategoryId(categoria.id);
    // Limpa mensagens de feedback antigas
    setError('');
    setSuccess('');
    // (UX) Rola a página para o topo (para o formulário)
    window.scrollTo(0, 0); 
  };

  /**
   * Chamado ao clicar no ícone de lixo (Excluir).
   * Chama 'DELETE /categorias/{id}'.
   */
  const handleDeleteClick = async (categoria) => {
    setError('');
    setSuccess('');

    // Confirmação de segurança nativa do navegador
    if (!window.confirm(`Tem certeza que deseja excluir a categoria "${categoria.nome}"?`)) {
      return;
    }

    try {
      await api.delete(`/categorias/${categoria.id}`);
      setSuccess(`Categoria "${categoria.nome}" excluída com sucesso.`);
      fetchCategorias(); // Atualiza a lista
    } catch (err) {
      console.error("Erro ao excluir categoria:", err);
      // (V8.1) Correção do Bug de Feedback
      // Se o backend retornar 400 (ex: "categoria em uso"),
      // exibe a mensagem de erro da API em um 'alert' (janela).
      if (err.response && err.response.status === 400 && err.response.data.detail) {
        window.alert(err.response.data.detail);
      } else {
        window.alert("Não foi possível excluir a categoria.");
      }
    }
  };

  /**
   * Chamado ao clicar no botão "Cancelar" (no modo de edição).
   */
  const handleCancelEdit = () => {
    resetForm();
    setError('');
    setSuccess('');
  };

  /**
   * Função principal de 'submit' do formulário.
   * Lida com POST (Criar) ou PUT (Editar) dependendo do 'isEditMode'.
   */
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    
    if (!nomeCategoria) {
      setError("O nome da categoria é obrigatório.");
      return;
    }

    // O "pacote" de dados para a API
    const categoriaPayload = {
      nome: nomeCategoria,
      tipo: tipoCategoria,
      cor: corCategoria
    };

    try {
      if (isEditMode) {
        // --- MODO DE EDIÇÃO (PUT /categorias/{id}) ---
        // (O schema 'CategoriaUpdate' no backend lida com
        //  o envio parcial, mas aqui enviamos o objeto completo)
        await api.put(`/categorias/${editingCategoryId}`, categoriaPayload);
        setSuccess(`Categoria "${nomeCategoria}" atualizada com sucesso!`);
      } else {
        // --- MODO DE CRIAÇÃO (POST /categorias/) ---
        await api.post('/categorias/', categoriaPayload);
        setSuccess(`Categoria "${nomeCategoria}" criada com sucesso!`);
      }
      
      resetForm();      // Limpa o formulário e sai do modo de edição
      fetchCategorias(); // Atualiza a lista

    } catch (err) {
      console.error("Erro ao salvar categoria:", err);
      // (Captura erros como "Nome duplicado" do backend)
      if (err.response && err.response.status === 400) {
        setError(err.response.data.detail);
      } else {
        setError("Erro ao salvar categoria. Tente novamente.");
      }
    }
  };

  return (
    <div className="settings-container">
      <header className="settings-header">
        <h2>Ajustes e Configurações</h2>
      </header>

      <main className="settings-content">
        
        {/* Card 1: Formulário de Categoria (Dinâmico) */}
        <div className="settings-card">
          {/* Título Dinâmico (V8.0) */}
          <h2>{isEditMode ? 'Editar Categoria' : 'Criar Nova Categoria'}</h2>
          
          <form onSubmit={handleSubmit}>
            {/* Feedback de Erro/Sucesso */}
            {error && <p className="error-message">{error}</p>}
            {success && <p className="success-message">{success}</p>}

            {/* Input Nome */}
            <div className="input-group">
              <label htmlFor="nome">Nome da Categoria</label>
              <input
                type="text"
                id="nome"
                value={nomeCategoria}
                onChange={(e) => setNomeCategoria(e.target.value)}
                placeholder="Ex: Combustível, Peças, Almoço"
              />
            </div>
            
            {/* Input Tipo */}
            <div className="input-group">
              <label htmlFor="tipo">Tipo</label>
              <select
                id="tipo"
                value={tipoCategoria}
                onChange={(e) => setTipoCategoria(e.target.value)}
              >
                <option value="Gasto">Gasto (Despesa)</option>
                <option value="Receita">Receita (Ganho)</option>
              </select>
            </div>

            {/* Input Cor (V5.0) */}
            <div className="input-group color-picker-group">
              <label htmlFor="cor">Cor (Aparecerá nos gráficos)</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <input
                  type="color"
                  id="cor"
                  value={corCategoria}
                  onChange={(e) => setCorCategoria(e.target.value)}
                />
                {/* Exibe o código hex da cor selecionada */}
                <span className="color-code-display" style={{ color: corCategoria }}>{corCategoria}</span>
              </div>
            </div>

            {/* Botões Dinâmicos (V8.0) */}
            <div className="form-button-group">
              <button type="submit" className="settings-button">
                {isEditMode ? 'Salvar Alterações' : 'Criar Categoria'}
              </button>
              
              {/* Só aparece se estivermos editando */}
              {isEditMode && (
                <button 
                  type="button" 
                  className="cancel-button" 
                  onClick={handleCancelEdit}
                >
                  Cancelar
                </button>
              )}
            </div>
          </form>
        </div>

        {/* Card 2: Lista de Categorias (V8.0) */}
        <div className="settings-card">
          <h2>Categorias Existentes</h2>
          <div className="categoria-list">
            {loading ? (
              <p>Carregando categorias...</p>
            ) : (
              <ul>
                {categorias.length === 0 ? (
                  <p>Nenhuma categoria encontrada.</p>
                ) : (
                  categorias.map((cat) => (
                    <li key={cat.id}>
                      {/* Lado Esquerdo: Cor, Nome, Tipo */}
                      <div className="categoria-info">
                        <span 
                          className="categoria-cor-preview" 
                          style={{ backgroundColor: cat.cor }}
                        ></span>
                        <span>{cat.nome}</span>
                        <span className={`tipo-badge-list tipo-${cat.tipo.toLowerCase()}`}>
                          {cat.tipo}
                        </span>
                      </div>
                      
                      {/* Lado Direito: Botões de Ação */}
                      <div className="categoria-list-actions">
                        <button className="edit-btn" title="Editar" onClick={() => handleEditClick(cat)}>
                          <IoPencil size={18} />
                        </button>
                        <button className="delete-btn" title="Excluir" onClick={() => handleDeleteClick(cat)}>
                          <IoTrash size={18} />
                        </button>
                      </div>
                    </li>
                  ))
                )}
              </ul>
            )}
          </div>
        </div>

        {/* Card 3: Aparência (V4.4) */}
        <div className="settings-card">
          <h2>Aparência</h2>
          <div className="settings-item">
            <span>Modo {theme === 'dark' ? 'Escuro' : 'Claro'}</span>
            <label className="theme-toggle">
              <input
                type="checkbox"
                onChange={toggleTheme}
                checked={theme === 'light'}
              />
              <span className="slider"></span>
            </label>
          </div>
        </div>

        {/* Card 4: Backup (Placeholder) */}
        <div className="settings-card">
          <h2>Segurança e Backup (V2.0)</h2>
          <div className="settings-item">
            <span>Exportar Backup de Dados</span>
            <button className="settings-button-disabled" disabled>
              Em breve
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Settings;