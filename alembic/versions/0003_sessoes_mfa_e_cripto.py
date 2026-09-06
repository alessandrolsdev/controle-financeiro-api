"""Sessões com refresh token, segundo fator e criptografia de PII.

Esta migração acompanha a segunda rodada da auditoria:

1. **Refresh tokens** persistidos por hash, com família de rotação — o que
   permite detectar reuso (indício de cópia vazada) e derrubar a sessão.
2. **Segundo fator TOTP** com códigos de recuperação de uso único.
3. **Criptografia de PII em repouso.** `nome_completo`, `email` e
   `observacoes` passam a ser gravados cifrados com AES-256-GCM. O e-mail
   ganha um índice cego (HMAC) para preservar unicidade e busca, já que o
   valor cifrado não é comparável.

O passo de cifragem lê e regrava cada registro usando a mesma chave que a
aplicação usará, então `ENCRYPTION_KEY` (ou `SECRET_KEY`, em desenvolvimento)
precisa estar definida com o valor definitivo antes de migrar.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from backend.core import cripto

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cifrar_coluna(bind, tabela: str, coluna: str) -> int:
    """Cifra em lote os valores já existentes de uma coluna.

    Registros nulos e valores que já carregam o prefixo de versão são
    ignorados, o que torna o passo seguro para reexecução.

    Args:
        bind: A conexão ativa da migração.
        tabela (str): Nome da tabela.
        coluna (str): Nome da coluna a cifrar.

    Returns:
        int: Quantidade de registros cifrados.
    """
    linhas = bind.execute(
        sa.text(
            f"SELECT id, {coluna} FROM {tabela} WHERE {coluna} IS NOT NULL"  # noqa: S608
        )
    ).all()

    total = 0
    for linha in linhas:
        valor = linha[1]
        if valor.startswith(cripto.PREFIXO_VERSAO):
            continue

        bind.execute(
            sa.text(
                f"UPDATE {tabela} SET {coluna} = :valor WHERE id = :id"  # noqa: S608
            ),
            {"valor": cripto.cifrar(valor), "id": linha[0]},
        )
        total += 1

    return total


def upgrade() -> None:
    """Cria as tabelas de sessão/MFA e cifra os dados pessoais existentes."""
    bind = op.get_bind()

    # --- Refresh tokens ---
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("familia_id", sa.String(length=36), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("usado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revogado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_revogacao", sa.String(length=64), nullable=True),
        sa.Column("ip_cliente", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_tokens_id"), "refresh_tokens", ["id"])
    op.create_index(
        op.f("ix_refresh_tokens_token_hash"),
        "refresh_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_refresh_tokens_familia_id"), "refresh_tokens", ["familia_id"]
    )
    op.create_index(
        op.f("ix_refresh_tokens_usuario_id"), "refresh_tokens", ["usuario_id"]
    )
    op.create_index(
        op.f("ix_refresh_tokens_expira_em"), "refresh_tokens", ["expira_em"]
    )
    op.create_index(
        "ix_refresh_token_usuario_familia",
        "refresh_tokens",
        ["usuario_id", "familia_id"],
    )

    # --- Códigos de recuperação ---
    op.create_table(
        "codigos_de_recuperacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo_hash", sa.String(length=255), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("usado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_codigos_de_recuperacao_id"), "codigos_de_recuperacao", ["id"]
    )
    op.create_index(
        op.f("ix_codigos_de_recuperacao_usuario_id"),
        "codigos_de_recuperacao",
        ["usuario_id"],
    )

    # --- Segundo fator no usuário ---
    op.add_column(
        "usuarios", sa.Column("mfa_secret", sa.String(length=512), nullable=True)
    )
    op.add_column(
        "usuarios",
        sa.Column(
            "mfa_ativado", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
    )
    op.add_column(
        "usuarios", sa.Column("mfa_ativado_em", sa.DateTime(timezone=True), nullable=True)
    )

    # --- Criptografia de PII ---
    # As colunas crescem porque o texto cifrado (nonce + tag + base64) ocupa
    # bem mais espaço que o valor original.
    op.add_column(
        "usuarios", sa.Column("email_indice", sa.String(length=64), nullable=True)
    )

    with op.batch_alter_table("usuarios") as batch:
        batch.alter_column(
            "nome_completo",
            type_=sa.String(length=512),
            existing_type=sa.String(length=255),
            existing_nullable=True,
        )
        batch.alter_column(
            "email",
            type_=sa.String(length=512),
            existing_type=sa.String(length=255),
            existing_nullable=True,
        )

    # O e-mail deixa de ser único em texto: a unicidade migra para o índice cego,
    # já que o mesmo endereço cifrado duas vezes produz textos diferentes.
    op.drop_index("ix_usuarios_email", table_name="usuarios")

    # O índice cego precisa ser calculado ANTES da cifragem, enquanto o e-mail
    # ainda está legível.
    for linha in bind.execute(
        sa.text("SELECT id, email FROM usuarios WHERE email IS NOT NULL")
    ).all():
        bind.execute(
            sa.text("UPDATE usuarios SET email_indice = :indice WHERE id = :id"),
            {"indice": cripto.indice_cego(linha[1]), "id": linha[0]},
        )

    _cifrar_coluna(bind, "usuarios", "nome_completo")
    _cifrar_coluna(bind, "usuarios", "email")
    _cifrar_coluna(bind, "transacoes", "observacoes")

    op.create_index(
        "ix_usuarios_email_indice", "usuarios", ["email_indice"], unique=True
    )


def downgrade() -> None:
    """Decifra os dados e remove as estruturas de sessão e MFA.

    A reversão descarta as sessões ativas e a configuração de segundo fator:
    os usuários precisarão fazer login de novo e reconfigurar o MFA.
    """
    bind = op.get_bind()

    for tabela, coluna in (
        ("usuarios", "nome_completo"),
        ("usuarios", "email"),
        ("transacoes", "observacoes"),
    ):
        linhas = bind.execute(
            sa.text(
                f"SELECT id, {coluna} FROM {tabela} WHERE {coluna} IS NOT NULL"  # noqa: S608
            )
        ).all()
        for linha in linhas:
            bind.execute(
                sa.text(
                    f"UPDATE {tabela} SET {coluna} = :valor WHERE id = :id"  # noqa: S608
                ),
                {"valor": cripto.decifrar(linha[1]), "id": linha[0]},
            )

    op.drop_index("ix_usuarios_email_indice", table_name="usuarios")
    op.drop_column("usuarios", "email_indice")

    with op.batch_alter_table("usuarios") as batch:
        batch.alter_column(
            "email",
            type_=sa.String(length=255),
            existing_type=sa.String(length=512),
            existing_nullable=True,
        )
        batch.alter_column(
            "nome_completo",
            type_=sa.String(length=255),
            existing_type=sa.String(length=512),
            existing_nullable=True,
        )

    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)

    op.drop_column("usuarios", "mfa_ativado_em")
    op.drop_column("usuarios", "mfa_ativado")
    op.drop_column("usuarios", "mfa_secret")

    op.drop_table("codigos_de_recuperacao")
    op.drop_table("refresh_tokens")
