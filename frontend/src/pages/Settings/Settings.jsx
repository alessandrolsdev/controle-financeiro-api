// Arquivo: frontend/src/pages/Settings/Settings.jsx
// (VERSÃO V3.0 - Refatorado para o MainLayout e "Glassmorphism")

import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import './Settings.css';
import { useTheme } from '../../context/ThemeContext';

function Settings() {
  const { theme, toggleTheme } = useTheme();
  const [categorias, setCategorias] = useState([]);
  const [loading, setLoading] = useState(true);

  const [nomeCategoria, setNomeCategoria] = useState('');
  const [tipoCategoria, setTipoCategoria] = useState('Gasto');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchCategorias = async () => {
    try {
      setLoading(true); // Liga o "carregando"
      const response = await api.get('/categorias/');
      setCategorias(response.data);
      setLoading(false); // Desliga o "carregando"
    } catch (err) {
      console.error("Erro ao buscar categorias:", err);
      setError("Não foi possível carregar as categorias.");
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCategorias();
  }, []);

  const handleCreateCategoria = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    if (!nomeCategoria) {
      setError("O nome da categoria é obrigatório.");
      return;
    }
    try {
      await api.post('/categorias/', {
        nome: nomeCategoria,
        tipo: tipoCategoria,
      });
      setSuccess(`Categoria "${nomeCategoria}" criada com sucesso!`);
      setNomeCategoria('');
      fetchCategorias(); // Atualiza a lista
    } catch (err) {
      console.error("Erro ao criar categoria:", err);
      setError("Erro ao criar categoria. Tente novamente.");
    }
  };

  return (

    // O 'settings-container' agora usa o padding-bottom para a Navbar
    <div className="settings-container">
      {/* O novo cabeçalho, igual ao do Dashboard */}
      <header className="settings-header">
        <h2>Ajustes e Configurações</h2>
      </header>

      <main className="settings-content">
        <div className="settings-card">
          <h2>Criar Nova Categoria</h2>
          <form onSubmit={handleCreateCategoria}>
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

            <button type="submit" className="settings-button">
              Criar Categoria
            </button>
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
                      <span>{cat.nome}</span>
                      <span className={`tipo-badge tipo-${cat.tipo.toLowerCase()}`}>
                        {cat.tipo}
                      </span>
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
            {/* Este é um interruptor (toggle) feito em CSS puro */}
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
            {/* O botão 'disabled' mostra que a feature existe no plano, mas não está pronta */}
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