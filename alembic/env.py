# Arquivo: alembic/env.py
"""Ambiente de Execução das Migrações Alembic.

A URL de conexão é obtida da configuração da aplicação (variável de ambiente
`DATABASE_URL`), nunca do `alembic.ini` — assim credenciais de produção não
transitam por arquivo versionado.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, event, pool

from backend.database import DATABASE_URL, Base
# Importar os modelos registra todas as tabelas no metadata, o que permite ao
# Alembic detectar diferenças automaticamente (`--autogenerate`).
from backend import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Injeta a URL resolvida pela aplicação.
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Executa as migrações em modo offline, emitindo SQL para stdout.

    Útil para revisão prévia do DDL por um DBA antes da aplicação em produção.
    """
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        # Necessário para que o SQLite consiga aplicar ALTERs via recriação
        # de tabela (batch mode).
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa as migrações conectando diretamente ao banco de dados."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    e_sqlite = connectable.dialect.name == "sqlite"

    if e_sqlite:

        @event.listens_for(connectable, "connect")
        def _desativar_fk_durante_migracao(dbapi_connection, connection_record):
            """Desativa a verificação de chaves estrangeiras no SQLite.

            O modo batch do Alembic aplica ALTERs no SQLite recriando a tabela
            (cria a nova, copia, apaga a antiga, renomeia). Com
            `foreign_keys=ON` — que a aplicação ativa em toda conexão SQLite — o
            passo de remoção viola as chaves estrangeiras que apontam para a
            tabela sendo recriada. A documentação do Alembic e do SQLite orienta
            desativar a verificação durante a migração.

            O `PRAGMA` precisa ser emitido aqui, no momento da conexão bruta:
            executado depois, dentro de uma transação já iniciada, o SQLite o
            ignora silenciosamente.

            Args:
                dbapi_connection: A conexão bruta do driver.
                connection_record: Metadados de pool do SQLAlchemy.
            """
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=OFF")
            cursor.close()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=e_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()

    if e_sqlite:
        # Verifica, em uma conexão nova, se a migração deixou alguma referência
        # órfã. Sem esta checagem a desativação acima poderia mascarar um erro
        # de backfill.
        with connectable.connect() as verificacao:
            violacoes = verificacao.exec_driver_sql(
                "PRAGMA foreign_key_check"
            ).fetchall()

        if violacoes:
            raise RuntimeError(
                f"A migração deixou violações de chave estrangeira: {violacoes}"
            )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
