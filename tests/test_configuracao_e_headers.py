# Arquivo: tests/test_configuracao_e_headers.py
"""Testes de Configuração Segura, Headers HTTP e Redação de Logs."""

from __future__ import annotations

import pytest
from conftest import cabecalho
from pydantic import ValidationError

from backend.core.config import Settings, descrever_configuracao
from backend.core.logging import redigir

# Chave de exemplo da documentação do FastAPI, publicada no README deste
# repositório entre o commit inicial e o commit 9211ad0.
CHAVE_VAZADA = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"

CHAVE_FORTE = "Xq7ZpL2mVn9RtKw4YbGc8HdJf5NsQe3AuIoPyTrEwZxCvBnMlKjHgFdSaQwErTyU"
CHAVE_FORTE_2 = "Mb4KpXw9ZqTr2LnVc7YsGd5HfJ8NeQ3AuIoPyRtEwZxCvBnMlKjHgFdSaQwErTyU"


def _config(**valores) -> Settings:
    """Constrói uma configuração isolada do ambiente e do arquivo .env.

    As variáveis de ambiente definidas pelo `conftest` (que apontam para o
    banco de teste) precisam ser neutralizadas, senão validações como
    "produção exige DATABASE_URL" nunca chegariam a falhar.

    Args:
        **valores: Campos da configuração.

    Returns:
        Settings: A configuração construída.
    """
    padroes = {"DATABASE_URL": None, "CORS_ORIGINS": [], "TRUSTED_HOSTS": ["*"]}
    return Settings(_env_file=None, **{**padroes, **valores})


def test_chave_publica_vazada_e_rejeitada():
    """A aplicação se recusa a subir com a chave que vazou pelo README.

    Qualquer implantação que tenha seguido as instruções antigas assina JWTs
    com uma chave de conhecimento público — ou seja, tokens forjáveis por
    qualquer pessoa.
    """
    with pytest.raises(ValidationError, match="comprometidos"):
        _config(SECRET_KEY=CHAVE_VAZADA)


@pytest.mark.parametrize(
    "chave",
    [
        "curta",                          # abaixo do mínimo
        "change-me" + "x" * 30,           # começa com placeholder mas é longa
        "a" * 40,                         # entropia insuficiente
    ],
)
def test_secret_key_fraca_e_rejeitada(chave):
    """Chaves curtas ou de baixa entropia impedem a inicialização.

    Args:
        chave (str): A chave fraca sob teste.
    """
    if chave == "change-me" + "x" * 30:
        # Este caso passa no comprimento; o que o barra é a variedade.
        with pytest.raises(ValidationError):
            _config(SECRET_KEY=chave)
        return

    with pytest.raises(ValidationError):
        _config(SECRET_KEY=chave)


def test_algoritmo_fora_da_allowlist_e_rejeitado():
    """Apenas HS256/384/512 são aceitos como algoritmo de assinatura."""
    with pytest.raises(ValidationError, match="não é permitido"):
        _config(SECRET_KEY=CHAVE_FORTE, ALGORITHM="none")


def test_producao_exige_banco_de_dados():
    """Em produção não há fallback silencioso para SQLite local."""
    with pytest.raises(ValidationError, match="DATABASE_URL é obrigatória"):
        _config(
            SECRET_KEY=CHAVE_FORTE,
            ENVIRONMENT="production",
            CORS_ORIGINS=["https://app.exemplo.com"],
            TRUSTED_HOSTS=["api.exemplo.com"],
        )


def test_producao_recusa_sqlite():
    """SQLite não é aceito como banco de produção."""
    with pytest.raises(ValidationError, match="SQLite não é suportado"):
        _config(
            SECRET_KEY=CHAVE_FORTE,
            ENVIRONMENT="production",
            DATABASE_URL="sqlite:///./app.db",
            CORS_ORIGINS=["https://app.exemplo.com"],
            TRUSTED_HOSTS=["api.exemplo.com"],
        )


def test_producao_recusa_cors_com_curinga():
    """Origens curinga são recusadas em produção.

    Com credenciais habilitadas, `*.vercel.app` permite que qualquer pessoa
    publique um site e leia os dados do usuário autenticado.
    """
    with pytest.raises(ValidationError, match="curinga"):
        _config(
            SECRET_KEY=CHAVE_FORTE,
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://u:p@host/db",
            CORS_ORIGINS=["https://*.vercel.app"],
            TRUSTED_HOSTS=["api.exemplo.com"],
        )


def test_producao_exige_https_no_cors():
    """Origens HTTP simples não são aceitas em produção."""
    with pytest.raises(ValidationError, match="HTTPS"):
        _config(
            SECRET_KEY=CHAVE_FORTE,
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://u:p@host/db",
            CORS_ORIGINS=["http://app.exemplo.com"],
            TRUSTED_HOSTS=["api.exemplo.com"],
        )


def test_producao_exige_cors_configurado():
    """Uma lista de origens vazia impede a inicialização em produção."""
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        _config(
            SECRET_KEY=CHAVE_FORTE,
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://u:p@host/db",
            CORS_ORIGINS=[],
            TRUSTED_HOSTS=["api.exemplo.com"],
        )


def test_configuracao_valida_de_producao_e_aceita():
    """Uma configuração correta de produção passa em todas as validações."""
    config = _config(
        SECRET_KEY=CHAVE_FORTE,
        ENCRYPTION_KEY=CHAVE_FORTE_2,
        ENVIRONMENT="production",
        DATABASE_URL="postgresql://usuario:senha@host/banco",
        CORS_ORIGINS=["https://app.exemplo.com"],
        TRUSTED_HOSTS=["api.exemplo.com"],
    )
    assert config.is_production


def test_resumo_de_configuracao_nao_expoe_segredos():
    """O resumo registrado em log oculta a chave e as credenciais do banco."""
    config = _config(
        SECRET_KEY=CHAVE_FORTE,
        ENCRYPTION_KEY=CHAVE_FORTE_2,
        DATABASE_URL="postgresql://usuario:senha_secreta@host/banco",
    )

    resumo = str(descrever_configuracao(config))

    assert CHAVE_FORTE not in resumo
    assert "senha_secreta" not in resumo
    assert "credenciais-ocultas" in resumo


@pytest.mark.parametrize(
    "texto,proibido",
    [
        ("senha=MinhaSenhaSecreta123", "MinhaSenhaSecreta123"),
        ('{"password": "hunter2xyz"}', "hunter2xyz"),
        ("postgresql://user:senhadobanco@host/db", "senhadobanco"),
        ("Authorization: Bearer abc.def.ghi", "abc.def.ghi"),
        (
            "token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhIn0.assinatura",
            "eyJhbGciOiJIUzI1NiJ9",
        ),
    ],
)
def test_redacao_remove_segredos_do_log(texto, proibido):
    """O filtro de log remove segredos antes da escrita.

    Args:
        texto (str): A linha de log de entrada.
        proibido (str): O trecho que não pode sobreviver à redação.
    """
    assert proibido not in redigir(texto)


def test_filtro_preserva_argumentos_nao_textuais():
    """O filtro de redação não pode quebrar formatações numéricas do logging.

    Converter todos os argumentos para string faz `"%d" % "200"` estourar
    `TypeError`, derrubando logs de bibliotecas de terceiros (httpx, uvicorn)
    que usam formatação numérica.
    """
    import logging

    from backend.core.logging import FiltroDeRedacao

    registro = logging.LogRecord(
        name="teste",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="status %d em %s com senha=%s",
        args=(200, "/token", "SegredoDoUsuario"),
        exc_info=None,
    )

    FiltroDeRedacao().filter(registro)
    mensagem = registro.getMessage()

    assert "status 200" in mensagem
    assert "SegredoDoUsuario" not in mensagem


def test_headers_de_seguranca_presentes(cliente):
    """Toda resposta carrega os cabeçalhos de defesa do navegador."""
    resposta = cliente.get("/")

    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
    assert resposta.headers["X-Frame-Options"] == "DENY"
    assert resposta.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in resposta.headers["Content-Security-Policy"]
    assert "no-store" in resposta.headers["Cache-Control"]


def test_resposta_com_dados_financeiros_nao_e_cacheavel(cliente, usuario_com_token):
    """Dados financeiros nunca são armazenados em cache compartilhado."""
    _, token = usuario_com_token

    resposta = cliente.get("/transacoes/", headers=cabecalho(token))

    assert "no-store" in resposta.headers["Cache-Control"]
    assert "private" in resposta.headers["Cache-Control"]


def test_id_de_correlacao_e_devolvido(cliente):
    """Toda resposta traz um `X-Request-ID` para rastreio."""
    assert cliente.get("/").headers.get("X-Request-ID")


def test_health_check_verifica_o_banco(cliente):
    """O health check confirma o acesso real ao banco de dados."""
    corpo = cliente.get("/health").json()
    assert corpo == {"status": "ok", "banco_de_dados": "ok"}


def test_corpo_grande_demais_e_rejeitado(cliente):
    """Corpos acima do limite recebem 413 sem serem processados."""
    resposta = cliente.post(
        "/usuarios/",
        content=b"x" * 2_000_000,
        headers={"Content-Type": "application/json"},
    )
    assert resposta.status_code == 413
