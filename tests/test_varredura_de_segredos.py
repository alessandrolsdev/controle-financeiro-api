# Arquivo: tests/test_varredura_de_segredos.py
"""Testes da Configuração da Varredura de Segredos.

A allowlist do gitleaks é o tipo de arquivo que silencia problemas quando fica
larga demais — e o estrago é invisível, porque uma varredura permissiva reporta
exatamente o mesmo "no leaks found" de uma varredura correta.

Estes testes fixam as duas propriedades que importam:

1. Os literais conhecidos do projeto (denylist de senhas fracas, fixtures de
   teste) não fazem a CI falhar.
2. Um segredo real plantado nos mesmos arquivos **continua sendo detectado**.

A segunda é a que protege de verdade. Uma versão anterior desta allowlist usava
`paths`, que dispensa o arquivo inteiro: a CI ficava verde e uma credencial
colada em `backend/security.py` passaria batida.

Os testes são pulados quando o binário do gitleaks não está disponível, para
não quebrar a suíte em máquinas que não o tenham.
"""

from __future__ import annotations

import os
import secrets
import shutil
import string
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = RAIZ / ".gitleaks.toml"

gitleaks = shutil.which("gitleaks")

pytestmark = pytest.mark.skipif(
    gitleaks is None, reason="binário do gitleaks não encontrado no PATH"
)


def _varrer(caminho: Path) -> tuple[int, str]:
    """Roda o gitleaks sobre um caminho usando a configuração do projeto.

    Args:
        caminho (Path): Arquivo ou diretório a varrer.

    Returns:
        tuple[int, str]: O código de saída e a saída combinada.
    """
    resultado = subprocess.run(  # noqa: S603 - binário resolvido por shutil.which
        [
            gitleaks,
            "dir",
            "--no-banner",
            "--config",
            str(CONFIG),
            str(caminho),
        ],
        capture_output=True,
        text=True,
        cwd=RAIZ,
        check=False,
    )
    return resultado.returncode, resultado.stdout + resultado.stderr


def test_configuracao_existe():
    """A configuração precisa estar versionada para a CI enxergá-la."""
    assert CONFIG.is_file()


@pytest.mark.parametrize(
    "arquivo",
    [
        "backend/security.py",
        "tests/test_configuracao_e_headers.py",
        "tests/conftest.py",
    ],
)
def test_literais_conhecidos_nao_disparam_alarme(arquivo):
    """Os literais legítimos do projeto passam pela varredura.

    Args:
        arquivo (str): O arquivo sob teste.
    """
    codigo, saida = _varrer(RAIZ / arquivo)
    assert codigo == 0, f"gitleaks acusou vazamento em {arquivo}:\n{saida}"


def _credencial_ficticia(formato: str) -> str:
    """Gera uma credencial fictícia em tempo de execução.

    Gerada, e não escrita como literal, de propósito: um literal aqui faria
    este próprio arquivo ser acusado pela varredura. E acrescentá-lo à
    allowlist para calar o alarme destruiria o teste — ele passaria a plantar
    um valor que a allowlist já dispensa, e não provaria mais nada.

    Args:
        formato (str): 'aws' para uma chave no formato da AWS, 'generico'
            para um token de alta entropia.

    Returns:
        str: A linha de código a ser acrescentada ao arquivo contaminado.
    """
    if formato == "aws":
        corpo = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16)
        )
        return f'AWS_ACCESS_KEY_ID = "AKIA{corpo}"'

    return f'api_key = "{secrets.token_urlsafe(32)}"'


@pytest.mark.parametrize(
    "arquivo,formato",
    [
        # Nos mesmos arquivos cobertos pela allowlist, para provar que a
        # dispensa é por conteúdo e não por caminho.
        ("backend/security.py", "aws"),
        ("tests/conftest.py", "generico"),
    ],
)
def test_segredo_real_continua_sendo_detectado(tmp_path, arquivo, formato):
    """Um segredo real plantado num arquivo da allowlist é detectado.

    Este é o teste que impede a allowlist de virar um silenciador. Ele falha se
    alguém acrescentar um filtro por `paths` — que dispensaria o arquivo todo.

    Args:
        tmp_path (Path): Diretório temporário do pytest.
        arquivo (str): O arquivo da allowlist a contaminar.
        formato (str): O formato da credencial fictícia a plantar.
    """
    original = (RAIZ / arquivo).read_text(encoding="utf-8")

    # A cópia preserva o caminho relativo, porque as regras podem depender dele.
    alvo = tmp_path / arquivo
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(
        f"{original}\n{_credencial_ficticia(formato)}\n", encoding="utf-8"
    )

    codigo, saida = _varrer(alvo)

    assert codigo != 0, (
        f"A allowlist escondeu um segredo real em {arquivo}. "
        "Provavelmente alguém acrescentou um filtro por `paths`, que dispensa "
        f"o arquivo inteiro.\nSaída do gitleaks:\n{saida}"
    )


def test_allowlist_nao_filtra_por_caminho():
    """A configuração não pode conter `paths`.

    Guarda de leitura, complementar ao teste de comportamento: torna a intenção
    explícita para quem for editar o arquivo, mesmo sem o gitleaks instalado.
    """
    conteudo = CONFIG.read_text(encoding="utf-8")

    linhas_de_configuracao = [
        linha.strip()
        for linha in conteudo.splitlines()
        if linha.strip() and not linha.strip().startswith("#")
    ]

    assert not any(
        linha.startswith("paths") for linha in linhas_de_configuracao
    ), (
        "A allowlist do gitleaks não deve filtrar por `paths`: isso dispensa o "
        "arquivo inteiro e esconderia um segredo real. Use `regexes` com o "
        "literal exato."
    )


def test_varredura_do_repositorio_esta_limpa():
    """O repositório inteiro passa na varredura com a configuração atual."""
    if os.environ.get("PULAR_VARREDURA_COMPLETA"):
        pytest.skip("varredura completa desativada por variável de ambiente")

    for caminho in ("backend", "tests", "alembic"):
        codigo, saida = _varrer(RAIZ / caminho)
        assert codigo == 0, f"gitleaks acusou vazamento em {caminho}/:\n{saida}"
