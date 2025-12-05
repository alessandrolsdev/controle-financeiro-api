# Arquivo: backend/database.py
"""Módulo de Conexão e Configuração do Banco de Dados.

Este módulo gerencia a criação da engine de conexão e da fábrica de sessões
do SQLAlchemy. Ele implementa uma lógica adaptativa para usar SQLite em
ambiente de desenvolvimento (caso a variável de ambiente DATABASE_URL não
esteja definida) e PostgreSQL em produção.

Attributes:
    DATABASE_URL (str): A URL de conexão com o banco de dados.
    engine (Engine): A instância da engine do SQLAlchemy.
    SessionLocal (sessionmaker): Fábrica de sessões de banco de dados configurada.
    Base (DeclarativeMeta): Classe base declarativa para os modelos ORM.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .core.config import settings

# --- Lógica de Conexão (Dev vs. Prod) ---

DATABASE_URL = settings.DATABASE_URL
is_sqlite = False

if not DATABASE_URL:
    print("AVISO: DATABASE_URL não encontrada. Usando banco de dados SQLite local (financeiro.db).")
    is_sqlite = True
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_NAME = "financeiro.db"
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, DB_NAME)}"
else:
    # Patch de compatibilidade para URLs antigas (Heroku/Render)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print("Usando banco de dados de produção (PostgreSQL).")

# --- Criação do Motor (Engine) ---

# Configuração específica para SQLite para permitir acesso de múltiplas threads
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args
)

# --- Criação da Fábrica de Sessões ---

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Criação da Base Declarativa ---

Base = declarative_base()
