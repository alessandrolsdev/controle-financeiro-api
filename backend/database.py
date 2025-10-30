# Arquivo: backend/database.py (versão corrigida)

import os # Importa a biblioteca para lidar com caminhos do sistema
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Obtém o caminho absoluto para o diretório onde este arquivo (database.py) está.
#    Ex: C:\...\controle-financeiro-api\backend
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 2. Define o nome do arquivo do banco de dados.
DB_NAME = "financeiro.db"

# 3. Cria a URL completa e absoluta para o banco de dados.
#    Isto garante que o banco de dados será criado NA PASTA 'backend'.
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, DB_NAME)}"


# 4. CRIA O "MOTOR" DO BANCO DE DADOS (ENGINE)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 5. CRIA UMA FÁBRICA DE SESSÕES
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 6. CRIA UMA BASE DECLARATIVA
Base = declarative_base()