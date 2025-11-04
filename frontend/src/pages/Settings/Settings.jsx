// Arquivo: frontend/src/pages/Settings/Settings.jsx
// Responsabilidade: "Página" (cômodo) de Configurações.
// Permite que o usuário crie e visualize as Categorias de transação.

import React, { useState, useEffect } from 'react';
import api from '../../services/api'; // Nosso "mensageiro" axios pré-configurado
import { Link } from 'react-router-dom'; // Para o botão "Voltar"
import './Settings.css';

/**
 * Componente da página de Configurações.
 * Exibe um formulário para criar novas categorias e uma lista das categorias existentes.
 */
function Settings() {
  // --- Estados de Dados ---
  const [categorias, setCategorias] = useState([]); // Armazena a lista de categorias vinda da API
  const [loading, setLoading] = useState(true);     // Controla a exibição da mensagem "Carregando..."
  
  // --- Estados do Formulário ---
  const [nomeCategoria, setNomeCategoria] = useState('');     // Controla o campo de "Nome"
  const [tipoCategoria, setTipoCategoria] = useState('Gasto'); // Controla o campo "Tipo"
  
  // --- Estados de Feedback (UI) ---
  const [error, setError] = useState('');       // Mensagem de erro do formulário
  const [success, setSuccess] = useState('');     // Mensagem de sucesso do formulário

  /**
   * Busca a lista de categorias na API.
   * Chamada pelo useEffect (ao carregar) e após criar uma nova categoria.
   */
  const fetchCategorias = async () => {
    try {
      // Usa nosso 'api.js', que já injeta o token de autenticação
      const response = await api.get('/categorias/'); 
      setCategorias(response.data);
      setLoading(false);
    } catch (err) {
      console.error("Erro ao buscar categorias:", err);
      setError("Não foi possível carregar as categorias.");
      setLoading(false);
    }
  };

  // Efeito "On Mount": Roda UMA VEZ quando o componente é carregado
  // O array vazio '[]' garante que ele só rode no carregamento inicial.
  useEffect(() => {
    fetchCategorias();
  }, []);

  /**
   * Lida com o envio (submit) do formulário de criação de categoria.
   */
  const handleCreateCategoria = async (event) => {
    event.preventDefault(); // Impede o recarregamento padrão da página
    setError('');
    setSuccess('');

    // Validação simples de frontend
    if (!nomeCategoria) {
      setError("O nome da categoria é obrigatório.");
      return;
    }

    try {
      // 1. Envia os dados do formulário (nome, tipo) para a API
      await api.post('/categorias/', {
        nome: nomeCategoria,
        tipo: tipoCategoria,
      });

      // 2. Feedback de Sucesso para o Usuário
      setSuccess(`Categoria "${nomeCategoria}" criada com sucesso!`);
      setNomeCategoria(''); // Limpa o campo do formulário

      // 3. ATUALIZAÇÃO EM TEMPO REAL:
      // Busca a lista de categorias novamente para que o usuário
      // veja a nova categoria aparecer na "Categorias Existentes"
      // sem precisar recarregar a página.
      fetchCategorias(); 
      
    } catch (err) {
      console.error("Erro ao criar categoria:", err);
      // Pega o erro específico do backend, se houver
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Erro ao criar categoria. Tente novamente.");
      }
    }
  };

  // --- Renderização do Componente (JSX) ---
  return (
    <div className="settings-container">
      {/* Barra de Navegação Específica da Página */}
      <nav className="settings-nav">
        <h1>Configurações</h1>
        <Link to="/" className="nav-link-back">
          &larr; Voltar ao Dashboard
        </Link>
      </nav>

      {/* Conteúdo Principal */}
      <main className="settings-content">
        
        {/* Card 1: Formulário de Criação */}
        <div className="settings-card">
          <h2>Criar Nova Categoria</h2>
          <form onSubmit={handleCreateCategoria}>
            {/* Exibe mensagens de feedback (erro ou sucesso) */}
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

        {/* Card 2: Lista de Categorias Existentes */}
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
                  // Loop (map) para renderizar cada item da lista
                  categorias.map((cat) => (
                    <li key={cat.id}>
                      <span>{cat.nome}</span>
                      {/* Badge (etiqueta) colorida para 'Gasto' ou 'Receita' */}
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