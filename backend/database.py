# Arquivo: backend/database.py
"""
Módulo de Conexão com Banco de Dados.

Este arquivo é responsável por configurar e criar a conexão
(o "motor" e a "sessão") com o banco de dados.

Decisão de Engenharia (Dev vs. Prod):
Este módulo é "inteligente":
1. Ele tenta ler a 'DATABASE_URL' (PostgreSQL) do 'core.config'.
2. Se não encontrar (em desenvolvimento local), ele cria
   automaticamente um banco de dados 'financeiro.db' (SQLite)
   na pasta 'backend/'.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Importa a 'settings' (nossa fonte única da verdade para URLs)
from .core.config import settings


# --- 1. Lógica de Conexão (Dev vs. Prod) ---

DATABASE_URL = settings.DATABASE_URL
is_sqlite = False

# Se a URL de produção (PostgreSQL) NÃO for encontrada,
# estamos em modo de desenvolvimento (SQLite).
if not DATABASE_URL:
    print("AVISO: DATABASE_URL não encontrada. Usando banco de dados SQLite local (financeiro.db).")
    is_sqlite = True
    
    # Cria o caminho absoluto para o nosso arquivo de banco local
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_NAME = "financeiro.db"
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, DB_NAME)}"
else:
    # Patch de compatibilidade:
    # Converte 'postgres://' (padrão antigo do Heroku/Render)
    # para 'postgresql://' (padrão oficial do SQLAlchemy).
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print("Usando banco de dados de produção (PostgreSQL).")

# --- 2. Criação do "Motor" (Engine) ---

# Prepara os argumentos de conexão.
# Decisão de Engenharia (SQLite Multi-thread):
# 'check_same_thread: False' é OBRIGATÓRIO para o SQLite
# funcionar com o FastAPI (que é multithread), mas
# quebraria a conexão com o PostgreSQL.
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args
)

# --- 3. Criação da "Fábrica de Sessões" ---

# 'SessionLocal' é uma 'fábrica' que cria novas sessões de banco de dados
# sempre que a dependência 'get_db()' é chamada em 'main.py'.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 4. Criação da Base Declarativa ---

# Todos os nossos 'models.py' (Usuario, Categoria, etc.) herdarão
# desta classe 'Base'. É como eles se registram no SQLAlchemy.
Base = declarative_base()