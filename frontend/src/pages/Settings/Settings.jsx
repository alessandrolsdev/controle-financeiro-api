// Arquivo: frontend/src/pages/Settings/Settings.jsx
/**
 * @file Página de Configurações.
 * @description Gerenciamento de categorias (CRUD) e configurações de aparência (tema).
 */

import { useState, useEffect } from 'react';
import api from '../../services/api';
import './Settings.css';
import { useTheme } from '../../context/useTheme';
import { IoPencil, IoTrash } from 'react-icons/io5';

import ImportSection from '../../components/ImportSection/ImportSection';
import SecuritySection from '../../components/SecuritySection/SecuritySection';

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
    <>
      <header className="cabecalho-pagina">
        <div>
          <h1>Ajustes</h1>
          <p>Categorias, importação, segurança e aparência.</p>
        </div>
      </header>

      <div className="config">
        {/* --- Categorias --- */}
        <section className="config-secao">
          <header>
            <h2>{isEditMode ? 'Editar categoria' : 'Nova categoria'}</h2>
            <p>Categorias definem se um lançamento é receita ou despesa.</p>
          </header>

          <div className="config-corpo">
            {error && <p className="mensagem mensagem-erro">{error}</p>}
            {success && <p className="mensagem mensagem-sucesso">{success}</p>}

            <form onSubmit={handleSubmit} className="form-linha">
              <div>
                <label className="rotulo" htmlFor="nome">
                  Nome
                </label>
                <input
                  id="nome"
                  className="campo"
                  value={nomeCategoria}
                  onChange={(e) => setNomeCategoria(e.target.value)}
                  placeholder="Combustível, Almoço, Salário…"
                  maxLength={100}
                  required
                />
              </div>

              <div>
                <label className="rotulo" htmlFor="tipo">
                  Tipo
                </label>
                <select
                  id="tipo"
                  className="campo"
                  value={tipoCategoria}
                  onChange={(e) => setTipoCategoria(e.target.value)}
                >
                  <option value="Gasto">Despesa</option>
                  <option value="Receita">Receita</option>
                </select>
              </div>

              <div>
                <label className="rotulo" htmlFor="cor">
                  Cor
                </label>
                <input
                  type="color"
                  id="cor"
                  className="seletor-cor"
                  value={corCategoria}
                  onChange={(e) => setCorCategoria(e.target.value)}
                />
              </div>

              <button type="submit" className="botao botao-primario">
                {isEditMode ? 'Salvar' : 'Adicionar'}
              </button>
            </form>

            {isEditMode && (
              <button
                type="button"
                className="botao botao-secundario"
                onClick={handleCancelEdit}
                style={{ alignSelf: 'flex-start' }}
              >
                Cancelar edição
              </button>
            )}
          </div>
        </section>

        <section className="config-secao">
          <header>
            <h2>Suas categorias</h2>
          </header>

          {loading ? (
            <p className="vazio">Carregando…</p>
          ) : categorias.length === 0 ? (
            <p className="vazio">Nenhuma categoria cadastrada.</p>
          ) : (
            <ul className="categorias">
              {categorias.map((cat) => (
                <li key={cat.id} className="categoria">
                  <span
                    className="categoria-cor"
                    style={{ backgroundColor: cat.cor }}
                    aria-hidden="true"
                  />
                  <span className="categoria-nome">{cat.nome}</span>
                  <span
                    className={
                      cat.tipo === 'Receita'
                        ? 'etiqueta etiqueta-receita'
                        : 'etiqueta etiqueta-gasto'
                    }
                  >
                    {cat.tipo === 'Receita' ? 'Receita' : 'Despesa'}
                  </span>

                  <div className="categoria-acoes">
                    <button
                      type="button"
                      className="botao-discreto"
                      onClick={() => handleEditClick(cat)}
                      aria-label={`Editar ${cat.nome}`}
                    >
                      <IoPencil size={15} />
                    </button>
                    <button
                      type="button"
                      className="botao-discreto"
                      onClick={() => handleDeleteClick(cat)}
                      aria-label={`Excluir ${cat.nome}`}
                    >
                      <IoTrash size={15} />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* --- Importação de planilha (issue #2) --- */}
        <ImportSection />

        {/* --- Segundo fator e sessões --- */}
        <SecuritySection />

        {/* --- Aparência --- */}
        <section className="config-secao">
          <header>
            <h2>Aparência</h2>
          </header>

          <div className="config-corpo">
            <div className="mfa-status">
              <span>Tema {theme === 'dark' ? 'escuro' : 'claro'}</span>
              <button
                type="button"
                className="botao botao-secundario"
                onClick={toggleTheme}
              >
                Usar tema {theme === 'dark' ? 'claro' : 'escuro'}
              </button>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}

export default Settings;
