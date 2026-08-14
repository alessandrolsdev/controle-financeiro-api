# Arquivo: backend/models.py
"""Módulo de Definição dos Modelos ORM (Object-Relational Mapping).

Define a estrutura das tabelas usando a sintaxe declarativa do SQLAlchemy 2.0.

Decisões relevantes para integridade financeira:

- **Categorias pertencem a um usuário.** Antes eram globais, o que permitia a
  qualquer usuário autenticado listar, renomear e apagar as categorias de todos
  os outros — e, com isso, corromper a classificação contábil alheia.
- **`tipo` é restrito por CHECK constraint.** O campo era texto livre, mas o
  dashboard só soma `'Gasto'` e `'Receita'`; uma categoria gravada como
  `'Despesa'` desaparecia silenciosamente dos totais. O banco agora rejeita
  qualquer valor fora do domínio.
- **`valor` é `Numeric(14, 2)` com CHECK de positividade.** O sinal da transação
  vem do tipo da categoria, nunca do valor, então valores negativos indicam
  corrupção de dados.
- **Idempotência de escrita.** `chave_idempotencia` com índice único por usuário
  impede que um retry de rede (ou a fila de sincronização offline) duplique um
  lançamento financeiro.
- **Trilha de auditoria imutável.** Toda escrita em transação registra quem fez,
  de onde, quando e quais valores mudaram.
- **`token_version`** permite invalidar todas as sessões de um usuário.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# Domínio fechado de tipos de categoria. O dashboard depende exatamente destes
# dois valores; qualquer outro faz o lançamento sumir dos totais.
TIPO_GASTO = "Gasto"
TIPO_RECEITA = "Receita"
TIPOS_DE_CATEGORIA = (TIPO_GASTO, TIPO_RECEITA)

# Teto de valor por lançamento, coerente com Numeric(14, 2).
VALOR_MAXIMO_TRANSACAO = Decimal("999999999999.99")


def agora_utc() -> datetime:
    """Retorna o instante atual em UTC, com fuso explícito.

    Substitui `datetime.utcnow`, que devolve um datetime ingênuo (sem fuso) e
    está depreciado. Timestamps ingênuos em um sistema financeiro produzem erros
    de janela em relatórios quando o servidor muda de fuso.

    Returns:
        datetime: O instante atual em UTC.
    """
    return datetime.now(UTC)


class Usuario(Base):
    """Representa um usuário do sistema na tabela 'usuarios'.

    Attributes:
        id (int): Identificador único do usuário (Chave Primária).
        nome_usuario (str): Nome de usuário único para login.
        senha_hash (str): Hash Argon2id da senha.
        token_version (int): Contador de invalidação de sessões. Incrementá-lo
            revoga todos os tokens JWT já emitidos para este usuário.
        nome_completo (Optional[str]): Nome completo do usuário.
        email (Optional[str]): Endereço de email do usuário (único).
        data_nascimento (Optional[datetime]): Data de nascimento do usuário.
        avatar_url (Optional[str]): URL para a imagem de avatar do usuário.
        criado_em (datetime): Data e hora de criação do registro.
        atualizado_em (datetime): Data e hora da última alteração.
        senha_alterada_em (datetime): Momento da última troca de senha.
        categorias (List[Categoria]): Categorias pertencentes ao usuário.
        transacoes (List[Transacao]): Transações do usuário.
    """

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # --- Informações de Autenticação ---
    nome_usuario: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )

    # --- Campos de Perfil ---
    nome_completo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    data_nascimento: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Metadados ---
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=agora_utc,
        server_default=func.now(),
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=agora_utc,
        onupdate=agora_utc, server_default=func.now(),
    )
    senha_alterada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=agora_utc,
        server_default=func.now(),
    )

    # --- Relacionamentos ---
    # `lazy="raise"` impede carregamento implícito (N+1) e, mais importante em
    # um contexto multiusuário, impede que uma coleção completa seja carregada
    # sem passar pelos filtros de escopo do módulo CRUD.
    categorias: Mapped[list[Categoria]] = relationship(
        back_populates="proprietario",
        lazy="raise",
        cascade="all, delete-orphan",
    )
    transacoes: Mapped[list[Transacao]] = relationship(
        back_populates="proprietario",
        lazy="raise",
        cascade="all, delete-orphan",
    )


class Categoria(Base):
    """Representa uma categoria de transação na tabela 'categorias'.

    Cada categoria pertence a exatamente um usuário. O nome é único apenas
    dentro do escopo daquele usuário.

    Attributes:
        id (int): Identificador único da categoria (Chave Primária).
        nome (str): Nome da categoria, único por usuário.
        tipo (str): 'Gasto' ou 'Receita', restrito por CHECK constraint.
        cor (str): Código hexadecimal da cor associada (ex.: '#FF0000').
        usuario_id (int): ID do usuário proprietário (Chave Estrangeira).
        criado_em (datetime): Data e hora de criação do registro.
        proprietario (Usuario): Usuário dono da categoria.
        transacoes (List[Transacao]): Transações classificadas nesta categoria.
    """

    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)

    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    cor: Mapped[str] = mapped_column(String(7), nullable=False, default="#CCCCCC")

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=agora_utc,
        server_default=func.now(),
    )

    # --- Relacionamentos ---
    proprietario: Mapped[Usuario] = relationship(back_populates="categorias")
    transacoes: Mapped[list[Transacao]] = relationship(
        back_populates="categoria", lazy="raise"
    )

    __table_args__ = (
        # Nome único por usuário (antes era único globalmente, o que vazava a
        # existência das categorias de outros usuários por colisão de nome).
        UniqueConstraint("usuario_id", "nome", name="uq_categoria_usuario_nome"),
        # Barreira final contra o bug contábil: o banco recusa qualquer tipo
        # fora do domínio conhecido pelo dashboard.
        CheckConstraint(
            "tipo IN ('Gasto', 'Receita')", name="ck_categoria_tipo_valido"
        ),
        # Formato #RRGGBB. A validação completa de hexadecimal fica no schema
        # Pydantic; aqui garantimos o formato básico de modo portável entre
        # SQLite e PostgreSQL.
        CheckConstraint(
            "length(cor) = 7 AND cor LIKE '#%'",
            name="ck_categoria_cor_formato",
        ),
    )


class Transacao(Base):
    """Representa uma transação financeira na tabela 'transacoes'.

    Attributes:
        id (int): Identificador único da transação (Chave Primária).
        descricao (str): Descrição ou título da transação.
        valor (Decimal): Valor monetário, sempre positivo.
        data (datetime): Data e hora da ocorrência da transação.
        observacoes (Optional[str]): Notas adicionais sobre a transação.
        chave_idempotencia (Optional[str]): Chave que impede duplicação em retry.
        categoria_id (int): ID da categoria associada (Chave Estrangeira).
        usuario_id (int): ID do usuário proprietário (Chave Estrangeira).
        criado_em (datetime): Data e hora de criação do registro.
        atualizado_em (datetime): Data e hora da última alteração.
        categoria (Categoria): Objeto da categoria associada.
        proprietario (Usuario): Objeto do usuário proprietário.
    """

    __tablename__ = "transacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)

    # Decisão de Engenharia: Numeric para precisão financeira exata.
    # Float jamais deve ser usado para dinheiro — 0.1 + 0.2 != 0.3 em binário.
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    data: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Chave enviada pelo cliente para tornar a criação idempotente.
    chave_idempotencia: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )

    # --- Chaves Estrangeiras ---
    # RESTRICT na categoria: apagar uma categoria em uso destruiria a
    # classificação contábil de lançamentos históricos.
    categoria_id: Mapped[int] = mapped_column(
        ForeignKey("categorias.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # --- Metadados ---
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=agora_utc,
        server_default=func.now(),
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=agora_utc,
        onupdate=agora_utc, server_default=func.now(),
    )

    # --- Relacionamentos ---
    categoria: Mapped[Categoria] = relationship(back_populates="transacoes")
    proprietario: Mapped[Usuario] = relationship(back_populates="transacoes")

    __table_args__ = (
        # Índice composto que atende às consultas de dashboard e extrato, que
        # sempre filtram por usuário e faixa de data.
        Index("ix_transacao_usuario_data", "usuario_id", "data"),
        # Garante que um retry com a mesma chave não crie um segundo lançamento.
        UniqueConstraint(
            "usuario_id", "chave_idempotencia", name="uq_transacao_idempotencia"
        ),
        # O sinal vem do tipo da categoria; um valor negativo inverteria o
        # resultado do dashboard silenciosamente.
        CheckConstraint("valor > 0", name="ck_transacao_valor_positivo"),
    )


class LogDeAuditoria(Base):
    """Trilha de auditoria imutável de operações sensíveis.

    Registra autenticação, alterações de credenciais e toda escrita sobre
    transações financeiras. É uma tabela append-only: a aplicação nunca emite
    UPDATE ou DELETE sobre ela.

    Attributes:
        id (int): Identificador único do registro.
        ocorrido_em (datetime): Momento do evento, em UTC.
        acao (str): Identificador da ação (ex.: 'transacao.criada').
        usuario_id (Optional[int]): Usuário responsável, se autenticado.
        nome_usuario (Optional[str]): Nome informado, preservado mesmo se a
            conta for removida ou o login falhar.
        entidade (Optional[str]): Tipo do recurso afetado.
        entidade_id (Optional[int]): Identificador do recurso afetado.
        sucesso (int): 1 para sucesso, 0 para falha.
        ip_cliente (Optional[str]): IP de origem da requisição.
        request_id (Optional[str]): ID de correlação com o log de requisições.
        detalhes (Optional[str]): Contexto adicional em JSON, sem dados sensíveis.
    """

    __tablename__ = "logs_auditoria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    ocorrido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=agora_utc,
        server_default=func.now(), index=True,
    )

    acao: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # SET NULL em vez de CASCADE: a trilha deve sobreviver à remoção da conta.
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    nome_usuario: Mapped[str | None] = mapped_column(String(100), nullable=True)

    entidade: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entidade_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    sucesso: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    ip_cliente: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    detalhes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_auditoria_usuario_data", "usuario_id", "ocorrido_em"),
        CheckConstraint("sucesso IN (0, 1)", name="ck_auditoria_sucesso_booleano"),
    )
