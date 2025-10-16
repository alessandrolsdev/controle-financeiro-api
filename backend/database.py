# Arquivo: backend/database.py
# Responsabilidade: Configurar a conexão com o banco de dados SQLite.

# Importa as ferramentas necessárias do SQLAlchemy, nossa biblioteca para trabalhar com bancos de dados.
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. DEFINE A URL DE CONEXÃO
#    "sqlite:///./financeiro.db" é a string de conexão.
#    - "sqlite:///" indica que estamos usando um banco de dados SQLite.
#    - "./financeiro.db" significa que o arquivo do banco de dados,
#      chamado 'financeiro.db', será criado na mesma pasta do projeto (o diretório 'backend').
SQLALCHEMY_DATABASE_URL = "sqlite:///./financeiro.db"


# 2. CRIA O "MOTOR" DO BANCO DE DADOS (ENGINE)
#    O 'engine' é o ponto de entrada principal para o SQLAlchemy se comunicar com o banco.
#    O argumento 'connect_args' é específico para o SQLite, para permitir que ele seja acessado
#    de múltiplas formas sem conflitos, o que é necessário para o FastAPI.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)


# 3. CRIA UMA FÁBRICA DE SESSÕES
#    Uma "sessão" é a principal interface para todas as interações com o banco de dados.
#    'SessionLocal' é uma classe. Cada vez que precisarmos conversar com o banco,
#    criaremos uma instância desta classe.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 4. CRIA UMA BASE DECLARATIVA
#    Nós vamos criar classes que representarão nossas tabelas (Usuario, Categoria, etc.).
#    Essas classes precisarão herdar desta classe 'Base' para que o SQLAlchemy
#    saiba que elas devem ser mapeadas para tabelas no banco de dados.
Base = declarative_base()