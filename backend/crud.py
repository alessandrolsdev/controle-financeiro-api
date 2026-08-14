# Arquivo: backend/crud.py
"""Módulo de Operações CRUD (Create, Read, Update, Delete).

Camada de abstração entre os endpoints da API e os modelos de dados.

Princípios aplicados neste módulo:

- **Escopo obrigatório por usuário.** Toda função que toca dados de um usuário
  recebe `usuario_id` e o aplica no `WHERE`. Não existe caminho que devolva ou
  altere o dado de outro usuário — nem para categorias, que antes eram globais.
- **Unidade de trabalho única.** Cada operação de escrita e seu respectivo
  registro de auditoria são gravados na *mesma* transação de banco. Ou os dois
  existem, ou nenhum existe.
- **Bloqueio pessimista em alterações financeiras.** Editar ou excluir uma
  transação usa `SELECT ... FOR UPDATE`, evitando que duas requisições
  simultâneas leiam o mesmo estado e produzam um resultado inconsistente.
- **Idempotência.** A criação aceita uma chave de idempotência; um retry com a
  mesma chave devolve o lançamento original em vez de criar um duplicado.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from . import models, schemas, security
from .core.logging import obter_logger

logger = obter_logger(__name__)

# Categorias criadas automaticamente para cada novo usuário, para que a conta
# seja utilizável desde o primeiro acesso sem depender de dados globais.
CATEGORIAS_PADRAO: tuple[tuple[str, str, str], ...] = (
    ("Alimentação", models.TIPO_GASTO, "#E74C3C"),
    ("Transporte", models.TIPO_GASTO, "#E67E22"),
    ("Moradia", models.TIPO_GASTO, "#9B59B6"),
    ("Saúde", models.TIPO_GASTO, "#1ABC9C"),
    ("Lazer", models.TIPO_GASTO, "#F1C40F"),
    ("Outros Gastos", models.TIPO_GASTO, "#95A5A6"),
    ("Salário", models.TIPO_RECEITA, "#2ECC71"),
    ("Vendas", models.TIPO_RECEITA, "#27AE60"),
    ("Outras Receitas", models.TIPO_RECEITA, "#16A085"),
)


# --- CONTEXTO DE AUDITORIA ---


class ContextoDeAuditoria:
    """Metadados de origem da requisição, propagados até a trilha de auditoria.

    Attributes:
        ip_cliente (Optional[str]): IP de origem da requisição.
        request_id (Optional[str]): ID de correlação com o log de requisições.
    """

    __slots__ = ("ip_cliente", "request_id")

    def __init__(
        self, ip_cliente: str | None = None, request_id: str | None = None
    ) -> None:
        """Inicializa o contexto.

        Args:
            ip_cliente (Optional[str]): IP de origem.
            request_id (Optional[str]): ID de correlação.
        """
        self.ip_cliente = ip_cliente
        self.request_id = request_id


def registrar_auditoria(
    db: Session,
    acao: str,
    *,
    usuario_id: int | None = None,
    nome_usuario: str | None = None,
    entidade: str | None = None,
    entidade_id: int | None = None,
    sucesso: bool = True,
    contexto: ContextoDeAuditoria | None = None,
    detalhes: dict[str, Any] | None = None,
) -> models.LogDeAuditoria:
    """Adiciona um registro à trilha de auditoria na sessão atual.

    O registro é apenas adicionado à sessão — o commit é responsabilidade de
    quem conduz a unidade de trabalho, de modo que a auditoria e a operação
    auditada compartilhem o mesmo destino transacional.

    Args:
        db (Session): Sessão ativa do banco de dados.
        acao (str): Identificador da ação (ex.: 'transacao.criada').
        usuario_id (Optional[int]): Usuário responsável.
        nome_usuario (Optional[str]): Nome informado, útil em falhas de login.
        entidade (Optional[str]): Tipo do recurso afetado.
        entidade_id (Optional[int]): Identificador do recurso afetado.
        sucesso (bool): Se a operação foi bem-sucedida.
        contexto (Optional[ContextoDeAuditoria]): Metadados da requisição.
        detalhes (Optional[dict[str, Any]]): Contexto adicional, sem segredos.

    Returns:
        models.LogDeAuditoria: O registro criado.
    """
    registro = models.LogDeAuditoria(
        acao=acao,
        usuario_id=usuario_id,
        nome_usuario=nome_usuario,
        entidade=entidade,
        entidade_id=entidade_id,
        sucesso=1 if sucesso else 0,
        ip_cliente=contexto.ip_cliente if contexto else None,
        request_id=contexto.request_id if contexto else None,
        detalhes=json.dumps(detalhes, ensure_ascii=False, default=str)
        if detalhes
        else None,
    )
    db.add(registro)
    return registro


# --- HELPERS DE PERÍODO ---


def _limites_do_periodo(
    data_inicio: date, data_fim: date
) -> tuple[datetime, datetime]:
    """Converte um intervalo de datas em um intervalo semiaberto de datetimes.

    O limite superior é exclusivo (`< início do dia seguinte`), o que inclui
    corretamente as transações registradas em qualquer horário do último dia.

    Args:
        data_inicio (date): Data inicial do período (inclusiva).
        data_fim (date): Data final do período (inclusiva).

    Returns:
        tuple[datetime, datetime]: Início inclusivo e fim exclusivo, em UTC.
    """
    inicio = datetime.combine(data_inicio, time.min, tzinfo=UTC)
    fim = datetime.combine(data_fim + timedelta(days=1), time.min, tzinfo=UTC)
    return inicio, fim


# --- FUNÇÕES CRUD (USUÁRIO) ---


def get_usuario_por_nome(db: Session, nome_usuario: str) -> models.Usuario | None:
    """Busca um registro de usuário pelo nome de usuário (username).

    Args:
        db (Session): Sessão ativa do banco de dados.
        nome_usuario (str): O nome de usuário a ser pesquisado.

    Returns:
        models.Usuario | None: O objeto usuário se encontrado, senão None.
    """
    return db.scalar(
        select(models.Usuario).where(models.Usuario.nome_usuario == nome_usuario)
    )


def get_usuario_por_id(db: Session, usuario_id: int) -> models.Usuario | None:
    """Busca um registro de usuário pelo identificador numérico.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario_id (int): O ID do usuário.

    Returns:
        models.Usuario | None: O objeto usuário se encontrado, senão None.
    """
    return db.get(models.Usuario, usuario_id)


def criar_usuario(
    db: Session,
    usuario: schemas.UsuarioCreate,
    contexto: ContextoDeAuditoria | None = None,
) -> models.Usuario:
    """Registra um novo usuário e provisiona suas categorias padrão.

    Tudo (usuário, categorias iniciais e auditoria) é gravado em uma única
    transação: uma conta não pode existir sem suas categorias.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario (schemas.UsuarioCreate): Dados do usuário para criação.
        contexto (Optional[ContextoDeAuditoria]): Metadados da requisição.

    Raises:
        IntegrityError: Se o nome de usuário já existir (violação de unicidade).

    Returns:
        models.Usuario: O objeto usuário recém-criado.
    """
    hash_da_senha = security.get_hash_da_senha(usuario.senha)

    db_usuario = models.Usuario(
        nome_usuario=usuario.nome_usuario,
        senha_hash=hash_da_senha,
        token_version=1,
    )
    db.add(db_usuario)

    # `flush` obtém o ID gerado sem encerrar a transação.
    db.flush()

    for nome, tipo, cor in CATEGORIAS_PADRAO:
        db.add(
            models.Categoria(
                nome=nome, tipo=tipo, cor=cor, usuario_id=db_usuario.id
            )
        )

    registrar_auditoria(
        db,
        "usuario.criado",
        usuario_id=db_usuario.id,
        nome_usuario=db_usuario.nome_usuario,
        entidade="usuario",
        entidade_id=db_usuario.id,
        contexto=contexto,
    )

    db.commit()
    db.refresh(db_usuario)
    return db_usuario


def atualizar_detalhes_usuario(
    db: Session,
    usuario: models.Usuario,
    detalhes: schemas.UsuarioUpdate,
    contexto: ContextoDeAuditoria | None = None,
) -> models.Usuario:
    """Atualiza as informações de perfil de um usuário existente.

    Apenas campos explicitamente enviados são alterados. Os campos permitidos
    vêm do schema, que proíbe atributos extras — não há caminho para escrever
    em `senha_hash` ou `token_version` por este endpoint.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario (models.Usuario): Instância do usuário a ser atualizada.
        detalhes (schemas.UsuarioUpdate): Novos dados para atualização.
        contexto (Optional[ContextoDeAuditoria]): Metadados da requisição.

    Raises:
        IntegrityError: Se o novo nome de usuário ou email já estiver em uso.

    Returns:
        models.Usuario: O objeto usuário atualizado.
    """
    update_data = detalhes.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(usuario, key, value)

    registrar_auditoria(
        db,
        "usuario.perfil_atualizado",
        usuario_id=usuario.id,
        nome_usuario=usuario.nome_usuario,
        entidade="usuario",
        entidade_id=usuario.id,
        contexto=contexto,
        # Registra apenas quais campos mudaram, nunca os valores.
        detalhes={"campos": sorted(update_data.keys())},
    )

    db.commit()
    db.refresh(usuario)
    return usuario


def mudar_senha_usuario(
    db: Session,
    usuario: models.Usuario,
    payload: schemas.UsuarioChangePassword,
    contexto: ContextoDeAuditoria | None = None,
) -> bool:
    """Altera a senha de acesso do usuário e revoga as sessões existentes.

    Incrementar `token_version` invalida imediatamente todos os tokens JWT já
    emitidos. Sem isso, quem trocasse a senha por suspeita de comprometimento
    continuaria com o invasor logado até o token expirar naturalmente.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario (models.Usuario): O usuário que está alterando a senha.
        payload (schemas.UsuarioChangePassword): Senha antiga e nova.
        contexto (Optional[ContextoDeAuditoria]): Metadados da requisição.

    Returns:
        bool: True se a senha foi alterada, False se a senha antiga não confere.
    """
    if not security.verificar_senha(payload.senha_antiga, usuario.senha_hash):
        registrar_auditoria(
            db,
            "usuario.troca_de_senha_negada",
            usuario_id=usuario.id,
            nome_usuario=usuario.nome_usuario,
            entidade="usuario",
            entidade_id=usuario.id,
            sucesso=False,
            contexto=contexto,
        )
        db.commit()
        return False

    usuario.senha_hash = security.get_hash_da_senha(payload.senha_nova)
    usuario.senha_alterada_em = models.agora_utc()
    # Revoga todos os tokens emitidos antes desta troca.
    usuario.token_version += 1

    registrar_auditoria(
        db,
        "usuario.senha_alterada",
        usuario_id=usuario.id,
        nome_usuario=usuario.nome_usuario,
        entidade="usuario",
        entidade_id=usuario.id,
        contexto=contexto,
        detalhes={"sessoes_revogadas": True},
    )

    db.commit()
    return True


def revogar_sessoes(
    db: Session,
    usuario: models.Usuario,
    contexto: ContextoDeAuditoria | None = None,
) -> int:
    """Invalida todos os tokens de acesso já emitidos para o usuário.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario (models.Usuario): O usuário alvo.
        contexto (Optional[ContextoDeAuditoria]): Metadados da requisição.

    Returns:
        int: A nova versão de credenciais.
    """
    usuario.token_version += 1

    registrar_auditoria(
        db,
        "usuario.sessoes_revogadas",
        usuario_id=usuario.id,
        nome_usuario=usuario.nome_usuario,
        entidade="usuario",
        entidade_id=usuario.id,
        contexto=contexto,
    )

    db.commit()
    return usuario.token_version


def registrar_tentativa_de_login(
    db: Session,
    nome_usuario: str,
    sucesso: bool,
    usuario_id: int | None = None,
    contexto: ContextoDeAuditoria | None = None,
) -> None:
    """Registra uma tentativa de autenticação na trilha de auditoria.

    Args:
        db (Session): Sessão ativa do banco de dados.
        nome_usuario (str): O nome informado na tentativa.
        sucesso (bool): Se a autenticação foi bem-sucedida.
        usuario_id (Optional[int]): O ID do usuário, quando identificado.
        contexto (Optional[ContextoDeAuditoria]): Metadados da requisição.
    """
    registrar_auditoria(
        db,
        "auth.login" if sucesso else "auth.login_falhou",
        usuario_id=usuario_id,
        # O nome é truncado para respeitar o limite da coluna mesmo quando a
        # tentativa usa um valor arbitrariamente longo.
        nome_usuario=nome_usuario[:100],
        entidade="usuario",
        entidade_id=usuario_id,
        sucesso=sucesso,
        contexto=contexto,
    )
    db.commit()


# --- FUNÇÕES CRUD (CATEGORIA) ---


def get_categoria_do_usuario(
    db: Session, categoria_id: int, usuario_id: int
) -> models.Categoria | None:
    """Busca uma categoria garantindo que ela pertence ao usuário informado.

    Este é o ponto único de resolução de categoria por ID. Qualquer caminho que
    aceite um `categoria_id` vindo do cliente passa por aqui, o que impede que
    um usuário referencie, edite ou apague a categoria de outro.

    Args:
        db (Session): Sessão ativa do banco de dados.
        categoria_id (int): ID da categoria.
        usuario_id (int): ID do usuário proprietário.

    Returns:
        models.Categoria | None: A categoria, ou None se não existir ou não
        pertencer ao usuário.
    """
    return db.scalar(
        select(models.Categoria).where(
            models.Categoria.id == categoria_id,
            models.Categoria.usuario_id == usuario_id,
        )
    )


def criar_categoria(
    db: Session,
    categoria: schemas.CategoriaCreate,
    usuario_id: int,
    contexto: ContextoDeAuditoria | None = None,
) -> models.Categoria:
    """Adiciona uma nova categoria pertencente ao usuário informado.

    Args:
        db (Session): Sessão ativa do banco de dados.
        categoria (schemas.CategoriaCreate): Dados da categoria.
        usuario_id (int): ID do usuário proprietário.
        contexto (Optional[ContextoDeAuditoria]): Metadados da requisição.

    Raises:
        IntegrityError: Se o usuário já tiver uma categoria com o mesmo nome.

    Returns:
        models.Categoria: O objeto categoria criado.
    """
    db_categoria = models.Categoria(
        nome=categoria.nome,
        tipo=categoria.tipo,
        cor=categoria.cor,
        usuario_id=usuario_id,
    )
    db.add(db_categoria)
    db.flush()

    registrar_auditoria(
        db,
        "categoria.criada",
        usuario_id=usuario_id,
        entidade="categoria",
        entidade_id=db_categoria.id,
        contexto=contexto,
        detalhes={"nome": db_categoria.nome, "tipo": db_categoria.tipo},
    )

    db.commit()
    db.refresh(db_categoria)
    return db_categoria


def listar_categorias(db: Session, usuario_id: int) -> list[models.Categoria]:
    """Retorna as categorias pertencentes ao usuário informado.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario_id (int): ID do usuário proprietário.

    Returns:
        list[models.Categoria]: Lista de categorias do usuário.
    """
    return list(
        db.scalars(
            select(models.Categoria)
            .where(models.Categoria.usuario_id == usuario_id)
            .order_by(models.Categoria.tipo, models.Categoria.nome)
        )
    )


def atualizar_categoria(
    db: Session,
    categoria_id: int,
    categoria_update: schemas.CategoriaUpdate,
    usuario_id: int,
    contexto: ContextoDeAuditoria | None = None,
) -> models.Categoria | None:
    """Atualiza uma categoria do usuário informado.

    Args:
        db (Session): Sessão ativa do banco de dados.
        categoria_id (int): ID da categoria a ser atualizada.
        categoria_update (schemas.CategoriaUpdate): Dados para atualização.
        usuario_id (int): ID do usuário proprietário.
        contexto (Optional[ContextoDeAuditoria]): Metadados da requisição.

    Raises:
        IntegrityError: Se o novo nome colidir com outra categoria do usuário.

    Returns:
        models.Categoria | None: A categoria atualizada, ou None se não
        encontrada para este usuário.
    """
    db_categoria = get_categoria_do_usuario(db, categoria_id, usuario_id)
    if not db_categoria:
        return None

    update_data = categoria_update.model_dump(exclude_unset=True)
    tipo_anterior = db_categoria.tipo

    for key, value in update_data.items():
        setattr(db_categoria, key, value)

    registrar_auditoria(
        db,
        "categoria.atualizada",
        usuario_id=usuario_id,
        entidade="categoria",
        entidade_id=db_categoria.id,
        contexto=contexto,
        detalhes={
            "campos": sorted(update_data.keys()),
            # Mudar o tipo reclassifica todo o histórico da categoria entre
            # receita e despesa, então o fato é registrado explicitamente.
            "tipo_anterior": tipo_anterior,
            "tipo_novo": db_categoria.tipo,
        },
    )

    db.commit()
    db.refresh(db_categoria)
    return db_categoria


def deletar_categoria(
    db: Session,
    categoria_id: int,
    usuario_id: int,
    contexto: ContextoDeAuditoria | None = None,
) -> bool:
    """Remove uma categoria do usuário informado.

    A exclusão é recusada se houver transações classificadas na categoria — a
    chave estrangeira usa `RESTRICT` justamente para preservar o histórico
    contábil.

    Args:
        db (Session): Sessão ativa do banco de dados.
        categoria_id (int): ID da categoria a ser removida.
        usuario_id (int): ID do usuário proprietário.
        contexto (Optional[ContextoDeAuditoria]): Metadados da requisição.

    Raises:
        IntegrityError: Se a categoria estiver em uso por alguma transação.

    Returns:
        bool: True se removida, False se não encontrada para este usuário.
    """
    db_categoria = get_categoria_do_usuario(db, categoria_id, usuario_id)
    if not db_categoria:
        return False

    nome = db_categoria.nome

    registrar_auditoria(
        db,
        "categoria.removida",
        usuario_id=usuario_id,
        entidade="categoria",
        entidade_id=categoria_id,
        contexto=contexto,
        detalhes={"nome": nome},
    )

    db.delete(db_categoria)
    db.commit()
    return True


def categoria_esta_em_uso(db: Session, categoria_id: int, usuario_id: int) -> bool:
    """Informa se existe alguma transação classificada na categoria.

    Args:
        db (Session): Sessão ativa do banco de dados.
        categoria_id (int): ID da categoria.
        usuario_id (int): ID do usuário proprietário.

    Returns:
        bool: True se houver ao menos uma transação usando a categoria.
    """
    total = db.scalar(
        select(func.count())
        .select_from(models.Transacao)
        .where(
            models.Transacao.categoria_id == categoria_id,
            models.Transacao.usuario_id == usuario_id,
        )
    )
    return bool(total)


# --- FUNÇÕES CRUD (TRANSAÇÃO) ---


def buscar_por_chave_de_idempotencia(
    db: Session, usuario_id: int, chave: str
) -> models.Transacao | None:
    """Recupera uma transação já criada com a mesma chave de idempotência.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario_id (int): ID do usuário proprietário.
        chave (str): A chave de idempotência informada pelo cliente.

    Returns:
        models.Transacao | None: A transação original, se já existir.
    """
    return db.scalar(
        select(models.Transacao)
        .options(joinedload(models.Transacao.categoria))
        .where(
            models.Transacao.usuario_id == usuario_id,
            models.Transacao.chave_idempotencia == chave,
        )
    )


def criar_transacao(
    db: Session,
    transacao: schemas.TransacaoCreate,
    usuario_id: int,
    chave_idempotencia: str | None = None,
    contexto: ContextoDeAuditoria | None = None,
) -> models.Transacao:
    """Registra uma nova transação financeira para um usuário.

    A categoria é resolvida dentro do escopo do usuário: referenciar a
    categoria de outra conta resulta em erro, não em um vínculo cruzado.

    Args:
        db (Session): Sessão ativa do banco de dados.
        transacao (schemas.TransacaoCreate): Dados da transação.
        usuario_id (int): ID do usuário proprietário.
        chave_idempotencia (Optional[str]): Chave que impede duplicação em retry.
        contexto (Optional[ContextoDeAuditoria]): Metadados da requisição.

    Raises:
        CategoriaInvalidaError: Se a categoria não pertencer ao usuário.

    Returns:
        models.Transacao: A transação criada (ou a original, em caso de retry).
    """
    if chave_idempotencia:
        existente = buscar_por_chave_de_idempotencia(
            db, usuario_id, chave_idempotencia
        )
        if existente is not None:
            logger.info(
                "Requisição idempotente: transação já existia",
                extra={"transacao_id": existente.id, "usuario_id": usuario_id},
            )
            return existente

    categoria = get_categoria_do_usuario(db, transacao.categoria_id, usuario_id)
    if categoria is None:
        raise CategoriaInvalidaError(transacao.categoria_id)

    db_transacao = models.Transacao(
        descricao=transacao.descricao,
        valor=transacao.valor,
        data=transacao.data,
        observacoes=transacao.observacoes,
        categoria_id=categoria.id,
        usuario_id=usuario_id,
        chave_idempotencia=chave_idempotencia,
    )
    db.add(db_transacao)

    try:
        db.flush()
    except IntegrityError:
        # Corrida entre dois retries simultâneos com a mesma chave: o índice
        # único barrou o segundo. Devolvemos o registro que venceu a corrida.
        db.rollback()
        if chave_idempotencia:
            existente = buscar_por_chave_de_idempotencia(
                db, usuario_id, chave_idempotencia
            )
            if existente is not None:
                return existente
        raise

    registrar_auditoria(
        db,
        "transacao.criada",
        usuario_id=usuario_id,
        entidade="transacao",
        entidade_id=db_transacao.id,
        contexto=contexto,
        detalhes={
            "valor": str(db_transacao.valor),
            "categoria_id": categoria.id,
            "tipo": categoria.tipo,
            "data": db_transacao.data.isoformat(),
        },
    )

    db.commit()
    db.refresh(db_transacao)
    return db_transacao


def atualizar_transacao(
    db: Session,
    transacao_id: int,
    transacao: schemas.TransacaoCreate,
    usuario_id: int,
    contexto: ContextoDeAuditoria | None = None,
) -> models.Transacao | None:
    """Atualiza uma transação existente, garantindo a propriedade do usuário.

    A linha é lida com bloqueio (`FOR UPDATE`) para que duas edições
    concorrentes sejam serializadas pelo banco, e a auditoria registra os
    valores anterior e novo.

    Args:
        db (Session): Sessão ativa do banco de dados.
        transacao_id (int): ID da transação a ser modificada.
        transacao (schemas.TransacaoCreate): Novos dados da transação.
        usuario_id (int): ID do usuário solicitante.
        contexto (Optional[ContextoDeAuditoria]): Metadados da requisição.

    Raises:
        CategoriaInvalidaError: Se a nova categoria não pertencer ao usuário.

    Returns:
        models.Transacao | None: A transação atualizada, ou None se não
        encontrada para este usuário.
    """
    db_transacao = db.scalar(
        _travar_para_atualizacao(
            select(models.Transacao).where(
                models.Transacao.id == transacao_id,
                models.Transacao.usuario_id == usuario_id,
            ),
            db,
        )
    )

    if db_transacao is None:
        return None

    categoria = get_categoria_do_usuario(db, transacao.categoria_id, usuario_id)
    if categoria is None:
        raise CategoriaInvalidaError(transacao.categoria_id)

    valor_anterior = db_transacao.valor
    categoria_anterior = db_transacao.categoria_id

    db_transacao.descricao = transacao.descricao
    db_transacao.valor = transacao.valor
    db_transacao.categoria_id = categoria.id
    db_transacao.data = transacao.data
    db_transacao.observacoes = transacao.observacoes

    registrar_auditoria(
        db,
        "transacao.atualizada",
        usuario_id=usuario_id,
        entidade="transacao",
        entidade_id=db_transacao.id,
        contexto=contexto,
        detalhes={
            "valor_anterior": str(valor_anterior),
            "valor_novo": str(db_transacao.valor),
            "categoria_anterior": categoria_anterior,
            "categoria_nova": categoria.id,
        },
    )

    db.commit()
    db.refresh(db_transacao)
    return db_transacao


def deletar_transacao(
    db: Session,
    transacao_id: int,
    usuario_id: int,
    contexto: ContextoDeAuditoria | None = None,
) -> bool:
    """Remove uma transação do banco de dados.

    Os valores do lançamento são preservados na trilha de auditoria antes da
    remoção, de modo que a exclusão continue rastreável.

    Args:
        db (Session): Sessão ativa do banco de dados.
        transacao_id (int): ID da transação a ser removida.
        usuario_id (int): ID do usuário solicitante.
        contexto (Optional[ContextoDeAuditoria]): Metadados da requisição.

    Returns:
        bool: True se removida, False se não encontrada para este usuário.
    """
    db_transacao = db.scalar(
        _travar_para_atualizacao(
            select(models.Transacao).where(
                models.Transacao.id == transacao_id,
                models.Transacao.usuario_id == usuario_id,
            ),
            db,
        )
    )

    if db_transacao is None:
        return False

    registrar_auditoria(
        db,
        "transacao.removida",
        usuario_id=usuario_id,
        entidade="transacao",
        entidade_id=transacao_id,
        contexto=contexto,
        detalhes={
            "valor": str(db_transacao.valor),
            "descricao": db_transacao.descricao,
            "categoria_id": db_transacao.categoria_id,
            "data": db_transacao.data.isoformat(),
        },
    )

    db.delete(db_transacao)
    db.commit()
    return True


def _travar_para_atualizacao(consulta: Select, db: Session) -> Select:
    """Aplica `FOR UPDATE` à consulta quando o banco suportar.

    O SQLite não implementa bloqueio em nível de linha (as escritas já são
    serializadas globalmente), então a cláusula é omitida nesse dialeto.

    Args:
        consulta (Select): A consulta a ser bloqueada.
        db (Session): Sessão ativa, usada para detectar o dialeto.

    Returns:
        Select: A consulta, com ou sem a cláusula de bloqueio.
    """
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        return consulta
    return consulta.with_for_update()


def listar_transacoes(
    db: Session, usuario_id: int, skip: int = 0, limit: int = 100
) -> list[models.Transacao]:
    """Retorna uma lista paginada das transações de um usuário.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario_id (int): ID do usuário cujas transações serão listadas.
        skip (int): Número de registros a pular (para paginação).
        limit (int): Número máximo de registros a retornar.

    Returns:
        list[models.Transacao]: Lista de transações encontradas.
    """
    return list(
        db.scalars(
            select(models.Transacao)
            .options(joinedload(models.Transacao.categoria))
            .where(models.Transacao.usuario_id == usuario_id)
            # `id` como critério de desempate garante ordenação estável entre
            # páginas quando várias transações têm a mesma data.
            .order_by(models.Transacao.data.desc(), models.Transacao.id.desc())
            .offset(skip)
            .limit(limit)
        )
    )


def listar_transacoes_por_periodo(
    db: Session,
    usuario_id: int,
    data_inicio: date,
    data_fim: date,
    limit: int = 5000,
) -> list[models.Transacao]:
    """Retorna as transações de um usuário em um intervalo de tempo.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario_id (int): ID do usuário.
        data_inicio (date): Data inicial do período (inclusiva).
        data_fim (date): Data final do período (inclusiva).
        limit (int): Teto de registros retornados, para proteger a memória.

    Returns:
        list[models.Transacao]: Lista de transações no período.
    """
    inicio, fim = _limites_do_periodo(data_inicio, data_fim)

    return list(
        db.scalars(
            select(models.Transacao)
            .options(joinedload(models.Transacao.categoria))
            .where(
                models.Transacao.usuario_id == usuario_id,
                models.Transacao.data >= inicio,
                models.Transacao.data < fim,
            )
            .order_by(models.Transacao.data.desc(), models.Transacao.id.desc())
            .limit(limit)
        )
    )


# --- FUNÇÕES ANALÍTICAS (DASHBOARD) ---


def get_dashboard_data(
    db: Session, usuario_id: int, data_inicio: date, data_fim: date
) -> schemas.DashboardData:
    """Calcula os dados consolidados para o dashboard financeiro.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario_id (int): ID do usuário.
        data_inicio (date): Data inicial do período de análise.
        data_fim (date): Data final do período de análise.

    Returns:
        schemas.DashboardData: Objeto com os dados processados.
    """
    inicio, fim = _limites_do_periodo(data_inicio, data_fim)

    def _total(tipo: str) -> Decimal:
        """Soma o valor das transações de um tipo de categoria no período.

        Args:
            tipo (str): 'Gasto' ou 'Receita'.

        Returns:
            Decimal: A soma, ou zero se não houver transações.
        """
        resultado = db.scalar(
            select(func.sum(models.Transacao.valor))
            .join(models.Categoria, models.Transacao.categoria_id == models.Categoria.id)
            .where(
                models.Transacao.usuario_id == usuario_id,
                models.Categoria.tipo == tipo,
                models.Transacao.data >= inicio,
                models.Transacao.data < fim,
            )
        )
        return resultado if resultado is not None else Decimal("0")

    def _por_categoria(tipo: str) -> list[schemas.CategoriaDetalhada]:
        """Agrega os totais por categoria para um tipo, no período.

        Args:
            tipo (str): 'Gasto' ou 'Receita'.

        Returns:
            list[schemas.CategoriaDetalhada]: Agregados ordenados por valor.
        """
        linhas = db.execute(
            select(
                models.Categoria.nome,
                models.Categoria.cor,
                func.sum(models.Transacao.valor).label("valor_total"),
                func.count(models.Transacao.id).label("total_compras"),
            )
            .join(
                models.Transacao,
                models.Transacao.categoria_id == models.Categoria.id,
            )
            .where(
                models.Transacao.usuario_id == usuario_id,
                models.Categoria.tipo == tipo,
                models.Transacao.data >= inicio,
                models.Transacao.data < fim,
            )
            # Agrupa por `id` para não fundir categorias homônimas; nome e cor
            # são funcionalmente dependentes da chave primária.
            .group_by(models.Categoria.id, models.Categoria.nome, models.Categoria.cor)
            .order_by(func.sum(models.Transacao.valor).desc())
        ).all()

        return [
            schemas.CategoriaDetalhada(
                nome_categoria=nome,
                cor=cor,
                valor_total=total,
                total_compras=contagem,
            )
            for nome, cor, total, contagem in linhas
        ]

    total_receitas = _total(models.TIPO_RECEITA)
    total_gastos = _total(models.TIPO_GASTO)

    return schemas.DashboardData(
        total_receitas=total_receitas,
        total_gastos=total_gastos,
        lucro_liquido=total_receitas - total_gastos,
        gastos_por_categoria=_por_categoria(models.TIPO_GASTO),
        receitas_por_categoria=_por_categoria(models.TIPO_RECEITA),
    )


def get_dados_de_tendencia(
    db: Session,
    usuario_id: int,
    data_inicio: date,
    data_fim: date,
    filtro: str,
) -> schemas.DadosDeTendencia:
    """Gera dados para gráficos de tendência financeira (evolução temporal).

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario_id (int): ID do usuário.
        data_inicio (date): Data inicial.
        data_fim (date): Data final.
        filtro (str): Granularidade ('daily' agrupa por hora, senão por dia).

    Returns:
        schemas.DadosDeTendencia: Dados formatados para plotagem.
    """
    inicio, fim = _limites_do_periodo(data_inicio, data_fim)
    dialeto = db.bind.dialect.name if db.bind is not None else "postgresql"

    if filtro == "daily":
        if dialeto == "postgresql":
            agrupador = func.to_char(models.Transacao.data, "YYYY-MM-DD HH24:00:00")
        else:
            agrupador = func.strftime("%Y-%m-%d %H:00:00", models.Transacao.data)
    else:
        if dialeto == "postgresql":
            # `to_char` mantém o resultado como texto nos dois ramos, evitando
            # que o mesmo endpoint devolva ora `date`, ora `str`.
            agrupador = func.to_char(models.Transacao.data, "YYYY-MM-DD")
        else:
            agrupador = func.strftime("%Y-%m-%d", models.Transacao.data)

    def _serie(tipo: str) -> list[schemas.PontoDeTendencia]:
        """Monta a série temporal agregada para um tipo de categoria.

        Args:
            tipo (str): 'Gasto' ou 'Receita'.

        Returns:
            list[schemas.PontoDeTendencia]: Pontos ordenados cronologicamente.
        """
        linhas = db.execute(
            select(
                agrupador.label("data"),
                func.sum(models.Transacao.valor).label("valor"),
            )
            .join(
                models.Categoria,
                models.Transacao.categoria_id == models.Categoria.id,
            )
            .where(
                models.Transacao.usuario_id == usuario_id,
                models.Categoria.tipo == tipo,
                models.Transacao.data >= inicio,
                models.Transacao.data < fim,
            )
            .group_by(agrupador)
            .order_by(agrupador)
        ).all()

        return [
            schemas.PontoDeTendencia(data=linha.data, valor=linha.valor)
            for linha in linhas
        ]

    return schemas.DadosDeTendencia(
        receitas=_serie(models.TIPO_RECEITA),
        despesas=_serie(models.TIPO_GASTO),
    )


# --- EXCEÇÕES DE DOMÍNIO ---


class CategoriaInvalidaError(Exception):
    """Sinaliza referência a uma categoria inexistente ou de outro usuário.

    Attributes:
        categoria_id (int): O ID que foi referenciado indevidamente.
    """

    def __init__(self, categoria_id: int) -> None:
        """Inicializa a exceção.

        Args:
            categoria_id (int): O ID de categoria informado na requisição.
        """
        self.categoria_id = categoria_id
        super().__init__(
            f"Categoria {categoria_id} não existe ou não pertence ao usuário."
        )
