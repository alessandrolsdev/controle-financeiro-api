# Arquivo: tests/conftest.py
"""Configuração compartilhada dos testes.

Cada teste roda contra um banco SQLite temporário próprio, criado a partir das
migrações do Alembic — e não de `create_all`. Isso faz com que a suíte valide
também as migrações, que são o que efetivamente roda em produção.
"""

from __future__ import annotations

import os
import secrets
import tempfile
from pathlib import Path

import pytest

# As variáveis precisam existir antes de qualquer import de `backend`, porque a
# configuração é carregada e validada no momento do import.
os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(64))
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
os.environ.setdefault("LOG_LEVEL", "WARNING")

_DIRETORIO_TEMPORARIO = tempfile.mkdtemp(prefix="nomad-testes-")
os.environ["DATABASE_URL"] = f"sqlite:///{_DIRETORIO_TEMPORARIO}/teste.db"

from fastapi.testclient import TestClient  # noqa: E402

from backend import models  # noqa: E402,F401
from backend.core import rate_limit  # noqa: E402
from backend.database import Base, engine  # noqa: E402
from backend.main import app  # noqa: E402

RAIZ_DO_PROJETO = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def banco_limpo():
    """Recria o esquema antes de cada teste, garantindo isolamento.

    Yields:
        None: Durante a execução do teste.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def limitador_limpo():
    """Zera o estado do rate limiter entre testes.

    Sem isso, um teste que esgota o limite de login faz os seguintes falharem.

    Yields:
        None: Durante a execução do teste.
    """
    rate_limit.resetar_limitador()
    yield
    rate_limit.resetar_limitador()


@pytest.fixture
def cliente() -> TestClient:
    """Fornece um cliente HTTP de teste para a aplicação.

    Returns:
        TestClient: Cliente configurado.
    """
    return TestClient(app)


SENHA_VALIDA = "SenhaForte#2026!nomad"


def criar_conta(
    cliente: TestClient, nome: str = "usuario_teste", senha: str = SENHA_VALIDA
) -> dict:
    """Cria uma conta e devolve os dados do usuário.

    Args:
        cliente (TestClient): Cliente HTTP de teste.
        nome (str): Nome de usuário desejado.
        senha (str): Senha em texto plano.

    Returns:
        dict: O corpo da resposta de criação.
    """
    resposta = cliente.post(
        "/usuarios/", json={"nome_usuario": nome, "senha": senha}
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def autenticar(
    cliente: TestClient, nome: str = "usuario_teste", senha: str = SENHA_VALIDA
) -> str:
    """Autentica e devolve o token CSRF da sessão aberta.

    Os tokens de sessão ficam em cookies `httpOnly`, que o `TestClient` guarda
    e reenvia sozinho. O que o teste precisa carregar adiante é o token CSRF,
    exigido nos métodos que alteram estado.

    Args:
        cliente (TestClient): Cliente HTTP de teste.
        nome (str): Nome de usuário.
        senha (str): Senha em texto plano.

    Returns:
        str: O token CSRF da sessão.
    """
    resposta = cliente.post(
        "/auth/login", data={"username": nome, "password": senha}
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["csrf_token"]


def cabecalho(token: str) -> dict[str, str]:
    """Monta os cabeçalhos de uma requisição autenticada por cookie.

    Args:
        token (str): O token CSRF devolvido por :func:`autenticar`.

    Returns:
        dict[str, str]: Cabeçalhos prontos para uso.
    """
    return {"X-CSRF-Token": token}


def cliente_autenticado(
    nome: str = "alice", senha: str = SENHA_VALIDA
) -> tuple[TestClient, str]:
    """Cria um cliente com sessão própria, isolado de outros clientes.

    Cada `TestClient` mantém seu próprio jar de cookies, então dois clientes
    representam dois navegadores distintos — o que é necessário para verificar
    isolamento entre usuários.

    Args:
        nome (str): Nome de usuário a criar.
        senha (str): Senha da conta.

    Returns:
        tuple[TestClient, str]: O cliente autenticado e seu token CSRF.
    """
    cliente = TestClient(app)
    criar_conta(cliente, nome, senha)
    return cliente, autenticar(cliente, nome, senha)


@pytest.fixture
def usuario_com_token(cliente: TestClient) -> tuple[dict, str]:
    """Cria uma conta autenticada pronta para uso.

    Args:
        cliente (TestClient): Cliente HTTP de teste.

    Returns:
        tuple[dict, str]: Os dados do usuário e o token CSRF da sessão.
    """
    usuario = criar_conta(cliente, "alice")
    token = autenticar(cliente, "alice")
    return usuario, token


@pytest.fixture
def dois_clientes() -> tuple[tuple[TestClient, str], tuple[TestClient, str]]:
    """Cria dois navegadores independentes, cada um com sua própria sessão.

    Com autenticação por cookie, dois usuários não podem compartilhar o mesmo
    `TestClient`: o segundo login sobrescreveria os cookies do primeiro.

    Returns:
        tuple: Pares (cliente, token CSRF) de 'alice' e 'bob'.
    """
    return cliente_autenticado("alice"), cliente_autenticado("bob")
