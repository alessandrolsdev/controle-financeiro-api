// Arquivo: frontend/src/pages/Settings/Settings.jsx
/**
 * @file Página de Configurações.
 * @description Gerenciamento de categorias (CRUD) e configurações de aparência (tema).
 */

import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import './Settings.css';
import { useTheme } from '../../context/ThemeContext';
import { IoPencil, IoTrash } from 'react-icons/io5';

/**
 * Componente de Configurações.
 *
 * Permite ao usuário:
 * - Criar, editar e excluir categorias de transações.
 * - Alternar o tema da aplicação (Claro/Escuro).
 *
 * @returns {JSX.Element} A página de configurações renderizada.
 */
function Settings() {
  const { theme, toggleTheme } = useTheme();
  
  const [categorias, setCategorias] = useState([]);
  const [loading, setLoading] = useState(true);

  // --- Estados do Formulário ---
  const [nomeCategoria, setNomeCategoria] = useState('');
  const [tipoCategoria, setTipoCategoria] = useState('Gasto');
  const [corCategoria, setCorCategoria] = useState('#FF7A00');
  
  const [editingCategoryId, setEditingCategoryId] = useState(null);
  const isEditMode = Boolean(editingCategoryId);

  // --- Estados de UI ---
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  /**
   * Busca a lista de categorias do backend.
   */
  const fetchCategorias = async () => {
    try {
      setLoading(true);
      const response = await api.get('/categorias/');
      setCategorias(response.data);
      setLoading(false);
    } catch (err) {
      console.error("Erro ao buscar categorias:", err);
      setError("Não foi possível carregar as categorias.");
      setLoading(false);
    }
  };

  /**
   * Efeito colateral para carregar categorias na montagem do componente.
   */
  useEffect(() => {
    fetchCategorias();
  }, []);

  /**
   * Reseta o formulário para o estado inicial (modo de criação).
   */
  const resetForm = () => {
    setNomeCategoria('');
    setTipoCategoria('Gasto');
    setCorCategoria('#FF7A00');
    setEditingCategoryId(null);
  };
  
  /**
   * Prepara o formulário para edição de uma categoria existente.
   * @param {object} categoria - A categoria a ser editada.
   */
  const handleEditClick = (categoria) => {
    setNomeCategoria(categoria.nome);
    setTipoCategoria(categoria.tipo);
    setCorCategoria(categoria.cor);
    setEditingCategoryId(categoria.id);
    setError('');
    setSuccess('');
    window.scrollTo(0, 0); 
  };

  /**
   * Remove uma categoria.
   * Solicita confirmação antes de excluir.
   * @param {object} categoria - A categoria a ser excluída.
   */
  const handleDeleteClick = async (categoria) => {
    setError('');
    setSuccess('');

    if (!window.confirm(`Tem certeza que deseja excluir a categoria "${categoria.nome}"?`)) {
      return;
    }

    try {
      await api.delete(`/categorias/${categoria.id}`);
      setSuccess(`Categoria "${categoria.nome}" excluída com sucesso.`);
      fetchCategorias();
    } catch (err) {
      console.error("Erro ao excluir categoria:", err);
      if (err.response && err.response.status === 400 && err.response.data.detail) {
        window.alert(err.response.data.detail);
      } else {
        window.alert("Não foi possível excluir a categoria.");
      }
    }
  };

  /**
   * Cancela a edição e limpa o formulário.
   */
  const handleCancelEdit = () => {
    resetForm();
    setError('');
    setSuccess('');
  };

  /**
   * Manipula o envio do formulário de categoria (Criação ou Edição).
   * @param {Event} event - O evento de submit.
   */
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    
    if (!nomeCategoria) {
      setError("O nome da categoria é obrigatório.");
      return;
    }

    const categoriaPayload = {
      nome: nomeCategoria,
      tipo: tipoCategoria,
      cor: corCategoria
    };

    try {
      if (isEditMode) {
        await api.put(`/categorias/${editingCategoryId}`, categoriaPayload);
        setSuccess(`Categoria "${nomeCategoria}" atualizada com sucesso!`);
      } else {
        await api.post('/categorias/', categoriaPayload);
        setSuccess(`Categoria "${nomeCategoria}" criada com sucesso!`);
      }
      
      resetForm();
      fetchCategorias();

    } catch (err) {
      console.error("Erro ao salvar categoria:", err);
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
        
        <div className="settings-card">
          <h2>{isEditMode ? 'Editar Categoria' : 'Criar Nova Categoria'}</h2>
          
          <form onSubmit={handleSubmit}>
            {error && <p className="error-message">{error}</p>}
            {success && <p className="success-message">{success}</p>}

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

            <div className="input-group color-picker-group">
              <label htmlFor="cor">Cor (Aparecerá nos gráficos)</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <input
                  type="color"
                  id="cor"
                  value={corCategoria}
                  onChange={(e) => setCorCategoria(e.target.value)}
                />
                <span className="color-code-display" style={{ color: corCategoria }}>{corCategoria}</span>
              </div>
            </div>

            <div className="form-button-group">
              <button type="submit" className="settings-button">
                {isEditMode ? 'Salvar Alterações' : 'Criar Categoria'}
              </button>
              
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
