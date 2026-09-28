# Arquivo: backend/database.py
"""Módulo de Conexão e Configuração do Banco de Dados.

Gerencia a engine de conexão e a fábrica de sessões do SQLAlchemy.

Decisões de engenharia:

- **`pool_pre_ping`**: bancos gerenciados (Render, RDS, Neon) encerram conexões
  ociosas sem avisar. Sem o ping de validação, a primeira requisição após um
  período de inatividade falha com `OperationalError`.
- **`expire_on_commit=False`**: permite que os objetos continuem legíveis depois
  do commit, evitando um SELECT extra durante a serialização da resposta.
- **Chaves estrangeiras no SQLite**: o SQLite ignora constraints de FK por
  padrão. Sem o `PRAGMA foreign_keys=ON`, o ambiente de desenvolvimento aceita
  dados que o PostgreSQL de produção rejeitaria.
- **Sem fallback silencioso em produção**: subir apontando para um SQLite local
  por causa de uma variável de ambiente ausente significaria gravar transações
  financeiras em um disco efêmero. A configuração impede isso.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from .core.config import settings
from .core.logging import obter_logger

logger = obter_logger(__name__)

# --- Resolução da URL de Conexão ---

DATABASE_URL = settings.DATABASE_URL
is_sqlite = False

if not DATABASE_URL:
    # A configuração já garante que isto só ocorre fora de produção.
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_NAME = "financeiro.db"
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, DB_NAME)}"
    is_sqlite = True
    logger.warning(
        "DATABASE_URL não definida. Usando SQLite local — apenas para desenvolvimento.",
        extra={"arquivo": DB_NAME},
    )
else:
    # Patch de compatibilidade para URLs antigas (Heroku/Render).
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )

    is_sqlite = DATABASE_URL.startswith("sqlite")

    if not is_sqlite:
        logger.info("Conectando ao banco de dados PostgreSQL.")

# --- Criação do Motor (Engine) ---

if is_sqlite:
    # `check_same_thread=False` é necessário porque o pool do SQLAlchemy pode
    # entregar a mesma conexão a threads diferentes do TestClient/uvicorn.
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        # StaticPool mantém um banco em memória vivo entre sessões nos testes.
        poolclass=StaticPool if ":memory:" in DATABASE_URL else None,
        echo=False,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        # Valida a conexão antes de usá-la: evita erros após ociosidade.
        pool_pre_ping=True,
        # Recicla conexões antes que o servidor as encerre por idade.
        pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
        # Falha rápido em vez de acumular requisições esperando conexão.
        pool_timeout=30,
        echo=False,
        connect_args={
            # Impede que uma consulta travada segure uma conexão para sempre.
            "options": "-c statement_timeout=30000",
            "application_name": "nomad-controle-financeiro",
        },
    )


@event.listens_for(Engine, "connect")
def _configurar_pragmas_sqlite(dbapi_connection, connection_record) -> None:
    """Ativa integridade referencial e o modo WAL em conexões SQLite.

    Sem `foreign_keys=ON` o SQLite aceita silenciosamente órfãos que o
    PostgreSQL rejeitaria, mascarando bugs até o deploy em produção.

    Args:
        dbapi_connection: A conexão bruta do driver.
        connection_record: Metadados de pool do SQLAlchemy.
    """
    # Detecta SQLite sem importar o módulo quando ele não estiver em uso.
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        # Garante que a escrita chegue ao disco antes de confirmar o commit.
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.close()


# --- Fábrica de Sessões ---

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    # Mantém os atributos acessíveis após o commit, evitando SELECTs extras
    # (e erros de DetachedInstance) durante a serialização da resposta.
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Classe base declarativa para todos os modelos ORM."""
