# API de Controle Financeiro

## 📖 Sobre o Projeto

Esta é uma API RESTful desenvolvida como solução para o controle financeiro de uma pequena empresa de terraplanagem. O objetivo principal é registrar despesas e receitas de forma eficiente, oferecendo uma base para futuras análises de dados e dashboards.

Este projeto foi construído seguindo as melhores práticas de engenharia de software, com uma arquitetura limpa no estilo MVC e um sistema de autenticação seguro baseado em Tokens JWT.

## 🚀 Tecnologias Utilizadas

- **Linguagem:** Python 3.12
- **Framework:** FastAPI
- **Banco de Dados:** SQLAlchemy com SQLite (para desenvolvimento)
- **Validação de Dados:** Pydantic
- **Segurança:** Passlib com Argon2 para hashing de senhas e Python-JOSE para Tokens JWT
- **Servidor ASGI:** Uvicorn

## ✨ Funcionalidades (MVP)

- [x] Criação segura de usuários com senha hasheada.
- [x] Autenticação de usuário via endpoint `/token` retornando um JWT.
- [x] Endpoints protegidos por autenticação.
- [x] CRUD completo para Categorias (Criar e Listar).
- [x] CRUD completo para Transações (Criar e Listar).

## ⚙️ Como Executar Localmente

Siga os passos abaixo para configurar e executar o projeto em seu ambiente local.

```bash
# 1. Clone o repositório
git clone [https://github.com/seu-usuario/controle-financeiro-api.git](https://github.com/seu-usuario/controle-financeiro-api.git)

# 2. Navegue até o diretório do projeto
cd controle-financeiro-api

# 3. Crie e ative um ambiente virtual
py -m venv venv
.\venv\Scripts\activate

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Inicie o servidor de desenvolvimento
# (Execute este comando a partir da pasta raiz 'controle-financeiro-api')
uvicorn backend.main:app --reload