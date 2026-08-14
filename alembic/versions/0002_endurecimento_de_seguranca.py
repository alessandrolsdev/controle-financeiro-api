"""Endurecimento de segurança e integridade contábil.

Esta migração aplica as correções da auditoria de segurança:

1. **Categorias passam a pertencer a um usuário.** Eram globais, o que permitia
   a qualquer usuário autenticado ler, renomear e apagar as categorias de todos
   os outros. O backfill preserva o histórico: cada categoria efetivamente usada
   é duplicada para o usuário que a utilizava, e suas transações são
   repontadas para a cópia.
2. **`tipo` restrito a 'Gasto'/'Receita' por CHECK.** O campo era texto livre,
   mas o dashboard só soma esses dois valores — uma categoria gravada como
   'Despesa' desaparecia dos totais sem qualquer erro.
3. **`token_version`** para permitir revogar sessões JWT.
4. **Idempotência** na criação de transações, evitando lançamentos duplicados
   por retry de rede ou pela fila de sincronização offline.
5. **Trilha de auditoria** append-only.
6. **Timestamps com fuso horário** e precisão monetária ampliada.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _e_postgres(bind) -> bool:
    """Informa se a conexão atual é PostgreSQL.

    Args:
        bind: A conexão ativa da migração.

    Returns:
        bool: True se o dialeto for PostgreSQL.
    """
    return bind.dialect.name == "postgresql"


def _verificar_valores_invalidos(bind) -> None:
    """Aborta a migração se existirem transações com valor não positivo.

    A nova constraint exige `valor > 0` (o sinal do lançamento vem do tipo da
    categoria). Corrigir esses registros automaticamente significaria alterar
    valores financeiros sem supervisão, então a migração para e exige revisão
    manual.

    Args:
        bind: A conexão ativa da migração.

    Raises:
        RuntimeError: Se houver transações com valor menor ou igual a zero.
    """
    total = bind.execute(
        sa.text("SELECT COUNT(*) FROM transacoes WHERE valor <= 0")
    ).scalar()

    if total:
        raise RuntimeError(
            f"Migração interrompida: {total} transação(ões) com valor <= 0. "
            "O novo esquema exige valores positivos (o sinal vem do tipo da "
            "categoria). Revise esses lançamentos manualmente antes de migrar:\n"
            "  SELECT id, descricao, valor, usuario_id FROM transacoes "
            "WHERE valor <= 0;"
        )


def _normalizar_dados(bind) -> None:
    """Normaliza os dados existentes para satisfazer as novas constraints.

    Args:
        bind: A conexão ativa da migração.
    """
    # 'Despesa' era o termo usado na documentação e nos schemas, mas o dashboard
    # sempre somou apenas 'Gasto'. Qualquer categoria gravada como 'Despesa'
    # estava invisível nos relatórios; aqui ela é trazida de volta.
    bind.execute(
        sa.text(
            "UPDATE categorias SET tipo = 'Gasto' "
            "WHERE LOWER(TRIM(tipo)) IN ('despesa', 'gasto', 'despesas', 'gastos')"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE categorias SET tipo = 'Receita' "
            "WHERE LOWER(TRIM(tipo)) IN ('receita', 'receitas', 'entrada', 'entradas')"
        )
    )
    # Qualquer valor remanescente fora do domínio vira 'Gasto', que é o caso
    # dominante e o mais conservador para não inflar receita.
    bind.execute(
        sa.text(
            "UPDATE categorias SET tipo = 'Gasto' "
            "WHERE tipo NOT IN ('Gasto', 'Receita')"
        )
    )

    # Cores fora do formato #RRGGBB quebrariam a nova constraint. Ajuste
    # puramente cosmético, sem impacto contábil.
    bind.execute(
        sa.text(
            "UPDATE categorias SET cor = '#CCCCCC' "
            "WHERE cor IS NULL OR LENGTH(cor) <> 7 OR cor NOT LIKE '#%'"
        )
    )


def _distribuir_categorias_por_usuario(bind) -> None:
    """Converte as categorias globais em categorias por usuário.

    Estratégia, executada em ordem para não perder nenhum vínculo:

    1. Para cada par (usuário, categoria) presente em `transacoes`, cria uma
       cópia da categoria pertencente àquele usuário e repõe as transações
       correspondentes na cópia.
    2. Categorias globais que ninguém usou são replicadas para todos os
       usuários, preservando a lista que eles já viam na interface.
    3. As linhas globais originais, agora sem nenhuma transação apontando para
       elas, são removidas.

    Args:
        bind: A conexão ativa da migração.
    """
    usuarios = [linha[0] for linha in bind.execute(sa.text("SELECT id FROM usuarios"))]

    # --- Etapa 1: categorias efetivamente em uso ---
    pares_em_uso = bind.execute(
        sa.text(
            "SELECT DISTINCT usuario_id, categoria_id FROM transacoes "
            "ORDER BY usuario_id, categoria_id"
        )
    ).all()

    for usuario_id, categoria_id in pares_em_uso:
        origem = bind.execute(
            sa.text(
                "SELECT nome, tipo, cor FROM categorias WHERE id = :cid"
            ),
            {"cid": categoria_id},
        ).first()

        if origem is None:
            # Transação órfã: a FK não era aplicada no SQLite, então esse
            # estado é possível em bases de desenvolvimento.
            continue

        novo_id = _inserir_categoria(
            bind, origem.nome, origem.tipo, origem.cor, usuario_id
        )

        bind.execute(
            sa.text(
                "UPDATE transacoes SET categoria_id = :novo "
                "WHERE usuario_id = :uid AND categoria_id = :antigo"
            ),
            {"novo": novo_id, "uid": usuario_id, "antigo": categoria_id},
        )

    # --- Etapa 2: categorias globais nunca usadas ---
    nao_usadas = bind.execute(
        sa.text(
            "SELECT id, nome, tipo, cor FROM categorias "
            "WHERE usuario_id IS NULL "
            "AND id NOT IN (SELECT DISTINCT categoria_id FROM transacoes)"
        )
    ).all()

    for categoria in nao_usadas:
        for usuario_id in usuarios:
            _inserir_categoria(
                bind, categoria.nome, categoria.tipo, categoria.cor, usuario_id
            )

    # --- Etapa 3: remove as linhas globais remanescentes ---
    bind.execute(sa.text("DELETE FROM categorias WHERE usuario_id IS NULL"))


def _inserir_categoria(bind, nome: str, tipo: str, cor: str, usuario_id: int) -> int:
    """Insere uma categoria para um usuário, reaproveitando uma já existente.

    Args:
        bind: A conexão ativa da migração.
        nome (str): Nome da categoria.
        tipo (str): 'Gasto' ou 'Receita'.
        cor (str): Cor em formato #RRGGBB.
        usuario_id (int): Usuário proprietário.

    Returns:
        int: O ID da categoria do usuário (nova ou preexistente).
    """
    existente = bind.execute(
        sa.text(
            "SELECT id FROM categorias WHERE usuario_id = :uid AND nome = :nome"
        ),
        {"uid": usuario_id, "nome": nome},
    ).scalar()

    if existente is not None:
        return existente

    if _e_postgres(bind):
        return bind.execute(
            sa.text(
                "INSERT INTO categorias (nome, tipo, cor, usuario_id) "
                "VALUES (:nome, :tipo, :cor, :uid) RETURNING id"
            ),
            {"nome": nome, "tipo": tipo, "cor": cor, "uid": usuario_id},
        ).scalar()

    resultado = bind.execute(
        sa.text(
            "INSERT INTO categorias (nome, tipo, cor, usuario_id) "
            "VALUES (:nome, :tipo, :cor, :uid)"
        ),
        {"nome": nome, "tipo": tipo, "cor": cor, "uid": usuario_id},
    )
    return resultado.lastrowid


def _adicionar_timestamp(bind, tabela: str, coluna: str) -> None:
    """Adiciona uma coluna de timestamp obrigatória a uma tabela existente.

    O SQLite recusa `ALTER TABLE ... ADD COLUMN` com default não constante
    (`CURRENT_TIMESTAMP`), então a coluna entra como nula, é preenchida com o
    instante atual e só depois é marcada como obrigatória — o que ocorre no
    bloco `batch_alter_table` correspondente, que recria a tabela.

    Args:
        bind: A conexão ativa da migração.
        tabela (str): Nome da tabela.
        coluna (str): Nome da coluna a criar.
    """
    op.add_column(tabela, sa.Column(coluna, sa.DateTime(timezone=True), nullable=True))
    bind.execute(
        sa.text(f"UPDATE {tabela} SET {coluna} = CURRENT_TIMESTAMP")  # noqa: S608
    )


def upgrade() -> None:
    """Aplica o endurecimento de segurança e integridade."""
    bind = op.get_bind()
    e_postgres = _e_postgres(bind)

    # Falha antes de qualquer alteração estrutural se houver dados que a nova
    # constraint rejeitaria.
    _verificar_valores_invalidos(bind)
    _normalizar_dados(bind)

    # --- Tabela: usuarios ---
    op.add_column(
        "usuarios",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="1"),
    )
    _adicionar_timestamp(bind, "usuarios", "atualizado_em")
    _adicionar_timestamp(bind, "usuarios", "senha_alterada_em")

    with op.batch_alter_table("usuarios") as batch:
        batch.alter_column(
            "atualizado_em",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )
        batch.alter_column(
            "senha_alterada_em",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )
        batch.alter_column(
            "criado_em",
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            postgresql_using="criado_em AT TIME ZONE 'UTC'" if e_postgres else None,
        )
        batch.alter_column(
            "data_nascimento",
            type_=sa.DateTime(timezone=True),
            existing_type=sa.Date(),
            existing_nullable=True,
            postgresql_using="data_nascimento::timestamptz" if e_postgres else None,
        )

    # --- Tabela: categorias ---
    # A coluna entra como nula para permitir o backfill, e só depois vira
    # obrigatória.
    op.add_column("categorias", sa.Column("usuario_id", sa.Integer(), nullable=True))
    _adicionar_timestamp(bind, "categorias", "criado_em")

    # O nome deixa de ser único globalmente: a unicidade passa a ser por usuário.
    op.drop_index("ix_categorias_nome", table_name="categorias")
    op.create_index("ix_categorias_nome", "categorias", ["nome"])

    _distribuir_categorias_por_usuario(bind)

    # As categorias criadas pelo backfill entram sem `criado_em`; preenche-as
    # antes de a coluna se tornar obrigatória.
    bind.execute(
        sa.text(
            "UPDATE categorias SET criado_em = CURRENT_TIMESTAMP "
            "WHERE criado_em IS NULL"
        )
    )

    with op.batch_alter_table("categorias") as batch:
        batch.alter_column("usuario_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column(
            "criado_em",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )
        batch.alter_column(
            "tipo", type_=sa.String(length=20), existing_type=sa.String(length=50)
        )
        batch.create_foreign_key(
            "fk_categoria_usuario",
            "usuarios",
            ["usuario_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_unique_constraint(
            "uq_categoria_usuario_nome", ["usuario_id", "nome"]
        )
        batch.create_check_constraint(
            "ck_categoria_tipo_valido", "tipo IN ('Gasto', 'Receita')"
        )
        batch.create_check_constraint(
            "ck_categoria_cor_formato", "length(cor) = 7 AND cor LIKE '#%'"
        )

    op.create_index("ix_categorias_usuario_id", "categorias", ["usuario_id"])

    # --- Tabela: transacoes ---
    op.add_column(
        "transacoes",
        sa.Column("chave_idempotencia", sa.String(length=64), nullable=True),
    )
    _adicionar_timestamp(bind, "transacoes", "criado_em")
    _adicionar_timestamp(bind, "transacoes", "atualizado_em")

    with op.batch_alter_table("transacoes") as batch:
        batch.alter_column(
            "criado_em",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )
        batch.alter_column(
            "atualizado_em",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )
        # Numeric(10,2) limitava o valor a ~99 milhões; 14,2 dá folga sem
        # abrir mão da precisão exata exigida para dinheiro.
        batch.alter_column(
            "valor",
            type_=sa.Numeric(precision=14, scale=2),
            existing_type=sa.Numeric(precision=10, scale=2),
            existing_nullable=False,
        )
        batch.alter_column(
            "data",
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=False,
            postgresql_using="data AT TIME ZONE 'UTC'" if e_postgres else None,
        )
        batch.create_unique_constraint(
            "uq_transacao_idempotencia", ["usuario_id", "chave_idempotencia"]
        )
        batch.create_check_constraint("ck_transacao_valor_positivo", "valor > 0")

    op.create_index("ix_transacao_usuario_data", "transacoes", ["usuario_id", "data"])
    op.create_index("ix_transacoes_categoria_id", "transacoes", ["categoria_id"])
    op.create_index("ix_transacoes_usuario_id", "transacoes", ["usuario_id"])

    # --- Tabela: logs_auditoria ---
    op.create_table(
        "logs_auditoria",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "ocorrido_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("acao", sa.String(length=64), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("nome_usuario", sa.String(length=100), nullable=True),
        sa.Column("entidade", sa.String(length=32), nullable=True),
        sa.Column("entidade_id", sa.Integer(), nullable=True),
        sa.Column("sucesso", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ip_cliente", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("detalhes", sa.Text(), nullable=True),
        # SET NULL preserva a trilha mesmo após a remoção da conta.
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("sucesso IN (0, 1)", name="ck_auditoria_sucesso_booleano"),
    )
    op.create_index(op.f("ix_logs_auditoria_id"), "logs_auditoria", ["id"])
    op.create_index(op.f("ix_logs_auditoria_acao"), "logs_auditoria", ["acao"])
    op.create_index(
        op.f("ix_logs_auditoria_ocorrido_em"), "logs_auditoria", ["ocorrido_em"]
    )
    op.create_index(
        op.f("ix_logs_auditoria_usuario_id"), "logs_auditoria", ["usuario_id"]
    )
    op.create_index(
        "ix_auditoria_usuario_data", "logs_auditoria", ["usuario_id", "ocorrido_em"]
    )


def downgrade() -> None:
    """Reverte o endurecimento.

    Atenção: a reversão é destrutiva. As categorias por usuário são consolidadas
    de volta em categorias globais (mantendo a primeira ocorrência de cada nome)
    e a trilha de auditoria é descartada.
    """
    bind = op.get_bind()

    op.drop_table("logs_auditoria")

    op.drop_index("ix_transacoes_usuario_id", table_name="transacoes")
    op.drop_index("ix_transacoes_categoria_id", table_name="transacoes")
    op.drop_index("ix_transacao_usuario_data", table_name="transacoes")

    with op.batch_alter_table("transacoes") as batch:
        batch.drop_constraint("ck_transacao_valor_positivo", type_="check")
        batch.drop_constraint("uq_transacao_idempotencia", type_="unique")
        batch.alter_column(
            "data",
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )
        batch.alter_column(
            "valor",
            type_=sa.Numeric(precision=10, scale=2),
            existing_type=sa.Numeric(precision=14, scale=2),
            existing_nullable=False,
        )

    op.drop_column("transacoes", "atualizado_em")
    op.drop_column("transacoes", "criado_em")
    op.drop_column("transacoes", "chave_idempotencia")

    # Consolida as categorias por usuário de volta em linhas globais únicas.
    bind.execute(
        sa.text(
            "UPDATE transacoes SET categoria_id = ("
            "  SELECT MIN(c2.id) FROM categorias c2 "
            "  WHERE c2.nome = (SELECT c1.nome FROM categorias c1 "
            "                   WHERE c1.id = transacoes.categoria_id)"
            ")"
        )
    )
    bind.execute(
        sa.text(
            "DELETE FROM categorias WHERE id NOT IN "
            "(SELECT MIN(id) FROM categorias GROUP BY nome)"
        )
    )

    op.drop_index("ix_categorias_usuario_id", table_name="categorias")

    with op.batch_alter_table("categorias") as batch:
        batch.drop_constraint("ck_categoria_cor_formato", type_="check")
        batch.drop_constraint("ck_categoria_tipo_valido", type_="check")
        batch.drop_constraint("uq_categoria_usuario_nome", type_="unique")
        batch.drop_constraint("fk_categoria_usuario", type_="foreignkey")
        batch.alter_column(
            "tipo", type_=sa.String(length=50), existing_type=sa.String(length=20)
        )

    op.drop_column("categorias", "criado_em")
    op.drop_column("categorias", "usuario_id")

    op.drop_index("ix_categorias_nome", table_name="categorias")
    op.create_index("ix_categorias_nome", "categorias", ["nome"], unique=True)

    with op.batch_alter_table("usuarios") as batch:
        batch.alter_column(
            "data_nascimento",
            type_=sa.Date(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=True,
        )
        batch.alter_column(
            "criado_em",
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )

    op.drop_column("usuarios", "senha_alterada_em")
    op.drop_column("usuarios", "atualizado_em")
    op.drop_column("usuarios", "token_version")
