# Arquivo: backend/database.py (VERSÃO REATORADA)
# Responsabilidade: Configurar a "tomada" (a conexão) com o banco de dados.
#
# REATORAÇÃO:
# Removemos a lógica 'load_dotenv' e 'os.getenv'.
# Agora, importamos a 'settings' do nosso módulo de configuração central.

import os # 'os' ainda é necessário para construir o caminho do SQLite
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# --- 1. IMPORTAÇÃO DA CONFIGURAÇÃO CENTRAL ---
# Em vez de carregar o .env, importamos nossa fonte única da verdade
from .core.config import settings


# --- 2. Lógica de Conexão Inteligente ---

# Lê a URL do banco de dados a partir da nossa configuração central
DATABASE_URL = settings.DATABASE_URL

# Variável de verificação para o 'engine'
is_sqlite = False

# A lógica de fallback permanece a MESMA.
# Se a 'DATABASE_URL' for None (conforme definido em config.py),
# caímos no modo de desenvolvimento SQLite.
if not DATABASE_URL:
    print("AVISO: DATABASE_URL não encontrada. Usando banco de dados SQLite local.")
    is_sqlite = True
    
    # Cria o caminho absoluto para o nosso arquivo de banco local
    # (A lógica 'BASE_DIR' foi simplificada pois 'os' já estava importado)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_NAME = "financeiro.db"
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, DB_NAME)}"
else:
    # Remove um aviso de depreciação do Heroku/Render
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print("Usando banco de dados de produção (PostgreSQL).")

# --- 3. Criação do "Motor" (Engine) ---

# A lógica permanece a mesma, pois 'is_sqlite' ainda é válido.
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args
)

# --- 4. Criação da "Fábrica de Sessões" ---

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 5. Criação da Base Declarativa ---
Base = declarative_base()