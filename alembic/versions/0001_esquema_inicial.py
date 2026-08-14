"""Esquema inicial (estado anterior à auditoria de segurança).

Reproduz o esquema que era criado por `Base.metadata.create_all()`, para que
instalações existentes possam ser marcadas com `alembic stamp 0001` e depois
seguir para as migrações seguintes sem recriar nada.

Revision ID: 0001
Revises:
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria as tabelas do esquema original."""
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome_usuario", sa.String(length=100), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("nome_completo", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("data_nascimento", sa.Date(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usuarios_id"), "usuarios", ["id"])
    op.create_index(op.f("ix_usuarios_nome_usuario"), "usuarios", ["nome_usuario"], unique=True)
    op.create_index(op.f("ix_usuarios_email"), "usuarios", ["email"], unique=True)

    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("tipo", sa.String(length=50), nullable=False),
        sa.Column("cor", sa.String(length=7), nullable=False, server_default="#CCCCCC"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_categorias_id"), "categorias", ["id"])
    op.create_index(op.f("ix_categorias_nome"), "categorias", ["nome"], unique=True)

    op.create_table(
        "transacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=False),
        sa.Column("valor", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("data", sa.DateTime(), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["categoria_id"], ["categorias.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transacoes_id"), "transacoes", ["id"])


def downgrade() -> None:
    """Remove as tabelas do esquema original."""
    op.drop_table("transacoes")
    op.drop_table("categorias")
    op.drop_table("usuarios")
