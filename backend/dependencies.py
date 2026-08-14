# Arquivo: backend/dependencies.py
"""Dependências Injetáveis da Aplicação.

Centraliza a sessão de banco, a resolução do usuário autenticado, o contexto de
auditoria e a aplicação de rate limiting.

Manter isso fora de `main.py` evita import circular e permite que os testes
substituam qualquer dependência individualmente.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import crud, models, security
from .core.config import settings
from .core.logging import obter_logger
from .core.middleware import obter_ip_do_cliente
from .core.rate_limit import verificar_limite
from .database import SessionLocal

logger = obter_logger(__name__)

# `auto_error=False` permite devolver a mesma resposta 401 genérica tanto para
# "sem cabeçalho" quanto para "token inválido", sem variar a mensagem.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Fornece uma sessão de banco de dados por requisição.

    Em caso de exceção, desfaz explicitamente qualquer trabalho pendente antes
    de devolver a conexão ao pool. Sem esse rollback, uma conexão com transação
    aberta volta ao pool e contamina a próxima requisição que a receber.

    Yields:
        Session: A sessão do banco de dados SQLAlchemy.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_contexto_de_auditoria(request: Request) -> crud.ContextoDeAuditoria:
    """Extrai os metadados de origem da requisição para a trilha de auditoria.

    Args:
        request (Request): A requisição atual.

    Returns:
        crud.ContextoDeAuditoria: Contexto com IP e ID de correlação.
    """
    return crud.ContextoDeAuditoria(
        ip_cliente=obter_ip_do_cliente(request),
        request_id=getattr(request.state, "request_id", None),
    )


def get_usuario_atual(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> models.Usuario:
    """Verifica o token JWT e retorna o usuário autenticado.

    Além de validar assinatura e claims, confere se a versão de credenciais do
    token ainda corresponde à do usuário. Um token emitido antes de uma troca de
    senha é rejeitado mesmo que ainda esteja dentro do prazo de expiração.

    Args:
        token (Optional[str]): O token JWT Bearer, se enviado.
        db (Session): Sessão do banco de dados.

    Raises:
        HTTPException: 401 se o token for ausente, inválido, expirado, revogado
            ou se o usuário não existir mais.

    Returns:
        models.Usuario: O objeto do usuário autenticado.
    """
    credentials_exception = security.criar_excecao_de_credenciais()

    if not token:
        raise credentials_exception

    payload = security.decodificar_token(token, credentials_exception)

    nome_usuario: str = payload["sub"]
    usuario_id = payload.get("uid")

    # Prefere a busca por ID (imutável) e recorre ao nome apenas para tokens
    # emitidos antes da introdução do claim `uid`.
    usuario: models.Usuario | None = None
    if isinstance(usuario_id, int):
        usuario = crud.get_usuario_por_id(db, usuario_id)
        # Impede que um token continue válido após o nome de usuário ser
        # transferido para outra conta.
        if usuario is not None and usuario.nome_usuario != nome_usuario:
            logger.warning(
                "Token rejeitado: nome de usuário divergente do ID",
                extra={"usuario_id": usuario_id},
            )
            raise credentials_exception
    else:
        usuario = crud.get_usuario_por_nome(db, nome_usuario=nome_usuario)

    if usuario is None:
        raise credentials_exception

    if payload["ver"] != usuario.token_version:
        logger.info(
            "Token rejeitado: credenciais revogadas",
            extra={"usuario_id": usuario.id},
        )
        raise credentials_exception

    return usuario


UsuarioAutenticado = Annotated[models.Usuario, Depends(get_usuario_atual)]
SessaoDB = Annotated[Session, Depends(get_db)]
Auditoria = Annotated[crud.ContextoDeAuditoria, Depends(get_contexto_de_auditoria)]


def aplicar_rate_limit(
    request: Request, escopo: str, limite: int, janela: int
) -> None:
    """Aplica rate limiting por IP a um escopo de endpoint.

    Args:
        request (Request): A requisição atual.
        escopo (str): Identificador do grupo de endpoints (ex.: 'login').
        limite (int): Máximo de requisições permitidas na janela.
        janela (int): Duração da janela em segundos.

    Raises:
        HTTPException: 429 quando o limite é excedido.
    """
    ip = obter_ip_do_cliente(request)
    resultado = verificar_limite(f"{escopo}:{ip}", limite, janela)

    if not resultado.permitido:
        logger.warning(
            "Rate limit excedido",
            extra={"escopo": escopo, "ip_cliente": ip},
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Tente novamente em instantes.",
            headers={"Retry-After": str(resultado.retry_after)},
        )


def rate_limit_login(request: Request) -> None:
    """Limita tentativas de autenticação por IP.

    Args:
        request (Request): A requisição atual.
    """
    aplicar_rate_limit(
        request,
        "login",
        settings.RATE_LIMIT_LOGIN,
        settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS,
    )


def rate_limit_cadastro(request: Request) -> None:
    """Limita criações de conta por IP.

    Args:
        request (Request): A requisição atual.
    """
    aplicar_rate_limit(
        request,
        "cadastro",
        settings.RATE_LIMIT_SIGNUP,
        settings.RATE_LIMIT_SIGNUP_WINDOW_SECONDS,
    )
