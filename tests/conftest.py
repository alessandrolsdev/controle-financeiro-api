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
    """Autentica e devolve o token de acesso.

    Args:
        cliente (TestClient): Cliente HTTP de teste.
        nome (str): Nome de usuário.
        senha (str): Senha em texto plano.

    Returns:
        str: O token JWT de acesso.
    """
    resposta = cliente.post(
        "/token", data={"username": nome, "password": senha}
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["access_token"]


def cabecalho(token: str) -> dict[str, str]:
    """Monta o cabeçalho de autorização Bearer.

    Args:
        token (str): O token de acesso.

    Returns:
        dict[str, str]: Cabeçalhos prontos para uso.
    """
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def usuario_com_token(cliente: TestClient) -> tuple[dict, str]:
    """Cria uma conta autenticada pronta para uso.

    Args:
        cliente (TestClient): Cliente HTTP de teste.

    Returns:
        tuple[dict, str]: Os dados do usuário e o token de acesso.
    """
    usuario = criar_conta(cliente, "alice")
    token = autenticar(cliente, "alice")
    return usuario, token


@pytest.fixture
def dois_usuarios(cliente: TestClient) -> tuple[str, str]:
    """Cria duas contas distintas e devolve seus tokens.

    Usado para verificar isolamento entre inquilinos.

    Args:
        cliente (TestClient): Cliente HTTP de teste.

    Returns:
        tuple[str, str]: Tokens de 'alice' e 'bob'.
    """
    criar_conta(cliente, "alice")
    criar_conta(cliente, "bob")
    return autenticar(cliente, "alice"), autenticar(cliente, "bob")
