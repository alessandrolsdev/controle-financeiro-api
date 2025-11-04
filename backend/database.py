# Arquivo: backend/database.py (VERSÃO FINAL - Produção e Desenvolvimento)
# Responsabilidade: Configurar a "tomada" (a conexão) com o banco de dados.
#
# Este arquivo é "inteligente":
# 1. Ele tenta ler a DATABASE_URL do arquivo .env (para o PostgreSQL na nuvem).
# 2. Se não encontrar, ele cria um banco SQLite local (para desenvolvimento).

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# --- 1. Carregamento das Variáveis de Ambiente ---

# Encontra o arquivo .env na pasta raiz do projeto (um nível acima de 'backend')
# O caminho de __file__ é 'backend/database.py', então precisamos de dois 'dirname'
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)


# --- 2. Lógica de Conexão Inteligente ---

# Tenta ler a URL do banco de dados de produção (PostgreSQL) do ambiente
DATABASE_URL = os.getenv("DATABASE_URL")

# Variável de verificação para o 'engine'
is_sqlite = False

# Se a URL de produção NÃO for encontrada, estamos em modo de desenvolvimento.
if not DATABASE_URL:
    print("AVISO: DATABASE_URL não encontrada. Usando banco de dados SQLite local.")
    is_sqlite = True
    
    # Cria o caminho absoluto para o nosso arquivo de banco local
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_NAME = "financeiro.db"
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, DB_NAME)}"
else:
    # Remove um aviso de depreciação do Heroku/Render
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print("Usando banco de dados de produção (PostgreSQL).")

# --- 3. Criação do "Motor" (Engine) ---

# Prepara os argumentos de conexão.
# O 'connect_args' é OBRIGATÓRIO para o SQLite em um app multithread
# (como o FastAPI), mas quebra o PostgreSQL.
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args
)

# --- 4. Criação da "Fábrica de Sessões" ---

# SessionLocal é uma 'fábrica' que cria novas sessões de banco de dados
# sempre que a dependência get_db() é chamada em main.py.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 5. Criação da Base Declarativa ---

# Todos os nossos 'models.py' (Usuario, Categoria, etc.) herdarão
# desta classe Base. É como eles se registram no SQLAlchemy.
Base = declarative_base()