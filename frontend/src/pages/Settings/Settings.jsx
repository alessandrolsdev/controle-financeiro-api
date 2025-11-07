// Arquivo: frontend/src/pages/Settings/Settings.jsx (VERSÃO V5.0 - COMPLETA COM SELETOR DE COR)
/*
REATORAÇÃO (Missão V5.0):
1. Adicionamos o estado 'corCategoria' e o input '<input type="color">'.
2. 'handleCreateCategoria' envia a cor para a API.
3. A lista de categorias exibe a cor da categoria (cat.cor).
*/

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
  // 1. NOVO ESTADO: Cor
  const [corCategoria, setCorCategoria] = useState('#FF7A00'); // Padrão: Laranja Voo
  
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchCategorias = async () => {
    try {
      setLoading(true);
      const response = await api.get('/categorias/');
      setCategorias(response.data);
      if (response.data.length > 0) {
        // Garantir que o select não comece vazio
        // (Nota: Nenhuma mudança aqui no select)
      }
      setLoading(false);
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
      // 2. ENVIA A COR PARA A API
      await api.post('/categorias/', {
        nome: nomeCategoria,
        tipo: tipoCategoria,
        cor: corCategoria // <-- ENVIANDO A COR
      });
      setSuccess(`Categoria "${nomeCategoria}" criada com sucesso!`);
      setNomeCategoria('');
      // setCorCategoria('#FF7A00'); // Opcional: reseta a cor, mas vamos deixar o usuário escolher
      fetchCategorias(); // Atualiza a lista
    } catch (err) {
      console.error("Erro ao criar categoria:", err);
      setError("Erro ao criar categoria. Tente novamente.");
    }
  };

  return (
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

            {/* 3. NOVO INPUT: Seletor de Cores */}
            <div className="input-group color-picker-group">
              <label htmlFor="cor">Cor (Aparecerá nos gráficos)</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <input
                  type="color" // <-- O INPUT MÁGICO
                  id="cor"
                  value={corCategoria}
                  onChange={(e) => setCorCategoria(e.target.value)}
                />
                <span className="color-code-display" style={{ color: corCategoria }}>{corCategoria}</span>
              </div>
            </div>

            <button type="submit" className="settings-button">
              Criar Categoria
            </button>
          </form>
        </div>

        {/* Categorias Existentes */}
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
                      {/* 4. EXIBINDO A COR DO BADGE (usando o estilo inline) */}
                      <span className="tipo-badge" style={{ backgroundColor: cat.cor }}>
                        {cat.tipo}
                      </span>
                    </li>
                  ))
                )}
              </ul>
            )}
          </div>
        </div>

        {/* Aparência */}
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

        {/* Segurança e Backup */}
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