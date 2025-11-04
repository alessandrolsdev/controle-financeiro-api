# 💸 API de Controle Financeiro (Projeto Full-Stack)

Este projeto é uma solução full-stack completa para o controle financeiro de uma pequena empresa, permitindo o registro de gastos e receitas em tempo real.

A aplicação é composta por um **Backend (API) ⚙️** construído em Python com FastAPI e um **Frontend (App) 🖥️** construído em React com Vite. Ambos estão implantados na nuvem.

## 🚀 DEMO EM PRODUÇÃO

* **Frontend (App React):** [https://controle-financeiro-api-eight.vercel.app](https://controle-financeiro-api-eight.vercel.app)
* **Backend (API FastAPI):** [https://controle-financeiro-api-ulpp.onrender.com/docs](https://controle-financeiro-api-ulpp.onrender.com/docs)

*(Nota: O banco de dados de produção pode ser reiniciado periodicamente. Credenciais de teste: `admin` / `admin`)*

---

## 🏛️ Arquitetura (Full-Stack Desacoplado)

Este projeto utiliza uma arquitetura moderna desacoplada, onde o Frontend (o "cliente") é totalmente separado do Backend (o "servidor").

`[ 🖥️ Frontend (React no Vercel) ]` --- (chama a API) ---> `[ ⚙️ Backend (FastAPI no Render) ]` --- (lê/escreve) ---> `[ 💾 Banco de Dados (PostgreSQL no Render) ]`

---

## ✨ Funcionalidades (MVP 1.0)

-   [x] **🔐 Autenticação Segura:** Criação de usuário com senhas hasheadas (Argon2) e sistema de login com Tokens JWT (Bearer).
-   [x] **🛡️ Endpoints Protegidos:** Todas as rotas de dados (`/transacoes`, `/categorias`, `/dashboard`) são 100% protegidas e só podem ser acessadas com um token válido.
-   [x] **🗂️ CRUD de Categorias:** O usuário pode criar e listar suas próprias categorias de gastos e receitas (ex: "Combustível", "Peças", "Serviço Prestado").
-   [x] **💸 Registro de Transações:** O usuário pode registrar um novo gasto ou receita através de um formulário modal.
-   [x] **📊 Dashboard em Tempo Real:** Um painel de controle que calcula e exibe automaticamente os totais de Receitas, Gastos e Lucro Líquido dos últimos 30 dias. O dashboard se atualiza instantaneamente após o registro de uma nova transação.
-   [x] **☁️ Deploy Contínuo:** O projeto está configurado com Git para deploy automático no Vercel (Frontend) e Render (Backend).

---

## 🛠️ Stack de Tecnologias

#### **Frontend (O "Cockpit" 🖥️)**
-   **⚛️ React 18** (com Hooks: `useState`, `useEffect`, `useContext`)
-   **⚡ Vite:** Ferramenta de build e servidor de desenvolvimento.
-   **🧭 React Router DOM:** Para roteamento de páginas (`/login`, `/`, `/settings`).
-   **🧠 React Context:** Para gerenciamento de estado global de autenticação (`AuthContext`).
-   **✉️ Axios:** Cliente HTTP para fazer requisições à API (com Interceptador para injetar o token JWT).
-   **🎨 CSS Puro:** Para estilização.

#### **Backend (O "Motor" ⚙️)**
-   **🐍 Python 3.12**
-   **🚀 FastAPI:** Framework web ASGI para construir a API.
-   **📋 Pydantic:** Para validação e "contrato" de dados (`schemas.py`).
-   **💾 SQLAlchemy (ORM):** "Tradutor" de Python para comandos SQL.
-   **🦄 Gunicorn:** Servidor de produção (rodando no Render).
-   **🔒 Segurança:**
    -   **Passlib (com Argon2):** Para hashing de senhas.
    -   **Python-JOSE:** Para criação e validação de Tokens JWT.

#### **Banco de Dados & DevOps ☁️**
-   **🐘 PostgreSQL:** Banco de dados relacional de produção (hospedado no Render).
-   **📄 SQLite:** Banco de dados de desenvolvimento local.
-   **R Render:** Plataforma de nuvem para deploy do Backend (API) e do Banco de Dados.
-   **V Vercel:** Plataforma de nuvem para deploy do Frontend (React).
-   **🐙 Git & GitHub:** Para controle de versão e deploy contínuo (CI/CD).

---

## ⚙️ Como Executar Localmente

Siga os passos abaixo para configurar e executar o projeto em seu ambiente local. Todos os comandos são executados da pasta raiz (`controle-financeiro-api`).

####  1. Clone o repositório
```bash
git clone [https://github.com/alessandrolsdev/controle-financeiro-api.git](https://github.com/alessandrolsdev/controle-financeiro-api.git)
cd controle-financeiro-api
```
#### --- Terminal 1 (Backend) ⚙️ ---

#### 2. Crie e ative o ambiente virtual (na pasta raiz)
```bash
py -m venv venv
.\venv\Scripts\activate
```
#### 3. Instale as dependências do Backend (o requirements.txt está na raiz)
```bash
pip install -r requirements.txt 
```
#### 4. Crie seu arquivo .env local (na pasta raiz)   (Obrigatório para a SECRET_KEY)
```bash
echo "SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7" > .env
echo "DATABASE_URL=" >> .env
```
#### 5. Inicie o servidor Backend (a partir da raiz)
```bash
uvicorn backend.main:app --reload
#### (O backend estará rodando em [http://127.0.0.1:8000](http://127.0.0.1:8000))
```

#### --- Terminal 2 (Frontend) 🖥️ ---

#### 6. Navegue até o frontend (em um novo terminal)
```bash
cd frontend
```
#### 7. Crie o .env do frontend
```bash
echo "VITE_API_BASE_URL=[http://127.0.0.1:8000](http://127.0.0.1:8000)" > .env
```
#### 8. Instale as dependências do Frontend
```bash
npm install
```
#### 9. Inicie o servidor Frontend
```bash
npm run dev

#### (O frontend estará rodando em http://localhost:5173)
```
Agora, você pode acessar http://localhost:5173 no seu navegador.

🛣️ Próximos Passos (Roadmap V2.0)
[ ] 📱 Modo Offline (PWA): Implementar um Service Worker (vite-plugin-pwa) para que o aplicativo seja instalável e permita o registro de gastos mesmo sem conexão com a internet.

[ ] 🎨 Responsividade: Melhorar o CSS para que a experiência em dispositivos móveis seja perfeita.

[ ] 🧩 GraphQL / Relay: Refatorar a API de REST para GraphQL e o cliente de dados de Axios/Context para Relay.

[ ] 💰 Contas Múltiplas: Adicionar a capacidade de gerenciar diferentes "contas" (ex: Poupança, Conta Corrente) para um balanço patrimonial.

---