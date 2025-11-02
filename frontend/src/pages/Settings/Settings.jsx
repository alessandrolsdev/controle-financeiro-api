// Arquivo: frontend/src/pages/Settings/Settings.jsx

import React, { useState, useEffect } from 'react';
import api from '../../services/api'; // Nosso 'api.js' com axios
import { Link } from 'react-router-dom'; // Para o botão "Voltar"
import './Settings.css';

function Settings() {
  const [categorias, setCategorias] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Estados para o formulário de nova categoria
  const [nomeCategoria, setNomeCategoria] = useState('');
  const [tipoCategoria, setTipoCategoria] = useState('Gasto'); // Padrão
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Função para buscar as categorias no backend
  const fetchCategorias = async () => {
    try {
      const response = await api.get('/categorias/'); // Usa nosso api.js (já tem o token)
      setCategorias(response.data);
      setLoading(false);
    } catch (err) {
      console.error("Erro ao buscar categorias:", err);
      setError("Não foi possível carregar as categorias.");
      setLoading(false);
    }
  };

  // useEffect: Busca as categorias quando a página carrega
  useEffect(() => {
    fetchCategorias();
  }, []); // O [] significa "execute apenas uma vez"

  // Função para lidar com o envio do formulário de nova categoria
  const handleCreateCategoria = async (event) => {
    event.preventDefault(); // Impede o recarregamento da página
    setError('');
    setSuccess('');

    if (!nomeCategoria) {
      setError("O nome da categoria é obrigatório.");
      return;
    }

    try {
      // Usa o 'api.js' para enviar a nova categoria para o backend
      await api.post('/categorias/', {
        nome: nomeCategoria,
        tipo: tipoCategoria,
      });

      setSuccess(`Categoria "${nomeCategoria}" criada com sucesso!`);
      setNomeCategoria(''); // Limpa o formulário
      fetchCategorias(); // Atualiza a lista de categorias na tela
      
    } catch (err) {
      console.error("Erro ao criar categoria:", err);
      setError("Erro ao criar categoria. Tente novamente.");
    }
  };

  return (
    <div className="settings-container">
      <nav className="settings-nav">
        <h1>Configurações</h1>
        <Link to="/" className="nav-link-back">
          &larr; Voltar ao Dashboard
        </Link>
      </nav>

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
      </main>
    </div>
  );
}

export default Settings;