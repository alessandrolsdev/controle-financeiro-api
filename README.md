# NOMAD - 💸 Aplicativo de Controle Financeiro (Full-Stack PWA)

O NOMAD é uma solução full-stack completa para o controle financeiro pessoal ou de pequenas empresas. Construído com uma arquitetura moderna desacoplada, o projeto é 100% gratuito, PWA (instalável), funciona offline e está implantado na nuvem.

Este projeto foi desenvolvido com uma mentalidade "production-ready", focando em performance, segurança e manutenibilidade.

## 🚀 DEMO EM PRODUÇÃO

* **Frontend (App React):** [https://controle-financeiro-api-eight.vercel.app](https://controle-financeiro-api-eight.vercel.app)
* **Backend (API FastAPI):** [https://controle-financeiro-api-ulpp.onrender.com/docs](https://controle-financeiro-api-ulpp.onrender.com/docs)

*(Nota: O banco de dados de produção (PostgreSQL Gratuito no Render) pode "dormir" (spin down) após 15 minutos de inatividade. O primeiro login do dia pode demorar até 2 minutos para "acordar" o servidor. Esta é a "troca" (trade-off) pelo deploy 100% gratuito.)*

---

## 🏛️ Arquitetura (Full-Stack Desacoplado)

Este projeto utiliza uma arquitetura moderna desacoplada, onde o Frontend (o "cliente") é totalmente separado do Backend (o "servidor").

`[ 🖥️ Frontend (React no Vercel) ]` --- (chama a API) ---> `[ ⚙️ Backend (FastAPI no Render) ]` --- (lê/escreve) ---> `[ 💾 Banco de Dados (PostgreSQL no Render) ]`

### Decisão de Arquitetura: Síncrono (Deploy Gratuito)

Inicialmente, o projeto foi desenhado com uma arquitetura assíncrona (Celery + Redis) para performance máxima. No entanto, para cumprir o requisito de um deploy **100% gratuito**, a arquitetura foi **revertida** para um modelo **Síncrono**.

O plano gratuito do Render não permite um *Web Service* (API) e um *Background Worker* (Celery) rodando simultaneamente. Portanto, o recálculo do dashboard (uma *query* lenta) é agora feito de forma síncrona pelo *endpoint* da API (`POST /transacoes/`), em vez de ser delegado a um *worker*.

* **Pró:** Custo de R$ 0.00.
* **Contra (O "Trade-off"):** O modal de "Salvar Transação" ficará mais lento (3-10 segundos) à medida que o banco de dados crescer.

---

## ✨ Funcionalidades (V3.0)

### Funcionalidades Principais (Backend & Frontend)
-   [x] **📱 PWA & Modo Offline:** A aplicação é 100% instalável (PWA). Graças ao `localStorage` e ao `AuthContext`, o usuário pode **criar transações offline**. Elas são salvas em uma "fila" e sincronizadas automaticamente com o backend assim que a conexão é restabelecida.
-   [x] **🔐 Autenticação & Perfil de Usuário (Full-Stack):**
    * Criação de conta (`POST /usuarios/`) com senhas hasheadas (Argon2).
    * Login (`POST /token`) com Tokens JWT (Bearer).
    * Gerenciamento de Perfil (`GET` e `PUT /usuarios/me`) para atualizar `nome_completo`, `email`, `data_nascimento` e `avatar_url`.
    * Mudança segura de `nome_usuario` (login), que força o logout (invalidando o token JWT antigo).
    * Mudança de Senha (`POST /usuarios/mudar-senha`) que valida a senha antiga.
-   [x] **💸 CRUD Completo de Transações:**
    * **C**reate: `POST /transacoes/` (no modal).
    * **R**ead: `GET /transacoes/periodo/` (no Dashboard).
    * **U**pdate: `PUT /transacoes/{id}` (o modal entra em "Modo de Edição").
    * **D**elete: `DELETE /transacoes/{id}` (o ícone de lixeira nas listas).
-   [x] **🗂️ CRUD Completo de Categorias:**
    * **C**reate: `POST /categorias/` (em "Ajustes").
    * **R**ead: `GET /categorias/` (para os *dropdowns*).
    * **U**pdate: `PUT /categorias/{id}` (para editar nome, tipo ou cor).
    * **D**elete: `DELETE /categorias/{id}` (com "trava" de segurança que impede a exclusão se a categoria estiver em uso).
-   [x] **🎨 Cores de Categoria Dinâmicas:** Usuários podem definir uma cor (hex code) para cada categoria, e os gráficos (Doughnut e Barras) usam essa cor dinamicamente.

### Funcionalidades de UI/UX
-   [x] **💡 Tema Claro / Escuro:** O `ThemeContext` salva a preferência do usuário no `localStorage` e aplica a UI (Dark/Light) dinamicamente.
-   [x] **📊 Dashboard & Relatórios Avançados:**
    * Filtro Global de Data (controlado pelo `MainLayout`) com 5 modos: Diário, Semanal, Mensal, Anual e **Personalizado** (com 2 calendários).
    * Gráficos de Rosca (Doughnut) no Dashboard que mostram Gastos/Receitas (com cores dinâmicas).
    * Gráfico de Linha (Tendência) na página de Relatórios que agrupa os dados **por hora** no filtro "Diário" (corrigindo a "linha reta") ou por dia nos demais filtros.
    * Gráficos de Barras Horizontais na página de Relatórios para "Gastos Detalhados" e "Receitas Detalhadas".
-   [x] **📄 Exportação para Excel:** A página de Relatórios permite exportar um arquivo `.xlsx` detalhado com 3 abas ("Extrato Geral", "Gastos", "Receitas") com base no filtro de data selecionado.
-   [x] **🛡️ Segurança de Sessão:** O interceptador do `api.js` detecta erros `401 Unauthorized` (token expirado) e redireciona o usuário para o login automaticamente.

---

## 🛠️ Stack de Tecnologias

#### **Frontend (O "Cockpit" 🖥️)**
-   **⚛️ React 18** (com Hooks: `useState`, `useEffect`, `useContext`)
-   **⚡ Vite:** Ferramenta de build e servidor de desenvolvimento.
-   **🧭 React Router DOM:** Para roteamento de páginas.
-   **🧠 React Context:** Para gerenciamento de estado global (`AuthContext`, `ThemeContext`).
-   **✉️ Axios:** Cliente HTTP para fazer requisições à API (com Interceptadores).
-   **🎨 CSS Puro:** Para estilização (com Variáveis CSS para o tema dinâmico).
-   **📱 Vite PWA:** Para o Service Worker e o cache offline.
-   **📊 Recharts:** Para os gráficos (Linha, Rosca, Barras).
-   **📄 XLSX (SheetJS):** Para a exportação de arquivos Excel.
-   **🎨 React Icons:** Para os ícones da UI.

#### **Backend (O "Motor" ⚙️)**
-   **🐍 Python 3.12**
-   **🚀 FastAPI:** Framework web ASGI para construir a API.
-   **📋 Pydantic (V2):** Para validação e "contrato" de dados (`schemas.py`), incluindo `pydantic-settings` e `email-validator`.
-   **💾 SQLAlchemy (ORM 2.0):** "Tradutor" de Python para comandos SQL (com sintaxe `Mapped`).
-   **🦄 Gunicorn:** Servidor de produção (rodando no Render).
-   **🔒 Segurança:**
    * **Passlib (com Argon2):** Para hashing de senhas.
    * **Python-JOSE:** Para criação e validação de Tokens JWT.

#### **Banco de Dados & DevOps ☁️**
-   **🐘 PostgreSQL:** Banco de dados relacional de produção (hospedado no Render).
-   **📄 SQLite:** Banco de dados de desenvolvimento local.
-   **R Render:** Plataforma de nuvem para deploy do Backend (API) e do Banco de Dados.
-   **V Vercel:** Plataforma de nuvem para deploy do Frontend (React).
-   **🐙 Git & GitHub:** Para controle de versão e deploy contínuo (CI/CD).

---

## ⚙️ Como Executar Localmente

Siga os passos abaixo para configurar e executar o projeto em seu ambiente local.

### --- Terminal 1 (Backend) ⚙️ ---


#### 1. Clone o repositório e entre na pasta
```bash
git clone [https://github.com/alessandrolsdev/controle-financeiro-api.git](https://github.com/alessandrolsdev/controle-financeiro-api.git)
cd controle-financeiro-api
```
#### 2. Crie e ative o ambiente virtual (na pasta raiz)
```bash
py -m venv venv
.\venv\Scripts\activate
```
#### 3. Instale as dependências do Backend
```bash
pip install -r requirements.txt 
```
#### 4. Crie seu arquivo .env local (na pasta raiz)
#### (O 'SECRET_KEY' é obrigatório)
#### (O 'DATABASE_URL' é opcional; sem ele, o app usará o 'financeiro.db' local)
```bash
echo "SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7" > .env
echo "DATABASE_URL=" >> .env
```
#### 5. Inicie o servidor Backend (a partir da raiz)
```bash
uvicorn backend.main:app --reload
```
#### (O backend estará rodando em [http://127.0.0.1:8000](http://127.0.0.1:8000))
### --- Terminal 2 (Frontend) 🖥️ ---

#### 6. Navegue até o frontend (em um novo terminal)
```bash
cd frontend
```
#### 7. Crie o .env do frontend
echo "VITE_API_BASE_URL=[http://127.0.0.1:8000](http://127.0.0.1:8000)" > .env

#### 8. Instale as dependências do Frontend
```bash
npm install
```
#### 9. Inicie o servidor Frontend
```bash
npm run dev
```
#### (O frontend estará rodando em http://localhost:5173)
🛣️ Próximos Passos (Roadmap V-Next)
[ ] Recuperação de Senha (V8.0): Implementar a lógica de "Esqueci minha senha" usando o email (exige um serviço de envio de email como SendGrid/Mailgun).

[ ] Upload de Avatar (V7.1): Substituir o avatar_url (link) por um upload de arquivo real (exige um serviço de armazenamento como S3 ou Cloudinary).

[ ] Contas Múltiplas: Adicionar a capacidade de gerenciar diferentes "contas" (ex: Poupança, Conta Corrente) para um balanço patrimonial.

[ ] WebSockets (V-Assíncrono): Se o app migrar para um plano pago, reativar o Celery/Redis e implementar WebSockets para que o dashboard atualize em tempo real (sem refresh) após a sincronização offline.