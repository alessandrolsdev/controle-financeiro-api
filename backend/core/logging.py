# Arquivo: backend/core/logging.py
"""Módulo de Logging Estruturado com Redação de Segredos.

Emite logs em JSON (adequado para agregadores como Datadog, Loki ou CloudWatch)
e aplica uma camada de redação que remove segredos antes de qualquer coisa ser
escrita. Isso vale inclusive para logs emitidos por bibliotecas de terceiros,
já que o filtro é instalado no logger raiz.

Motivação: senhas, tokens JWT e URLs de banco com credenciais costumam vazar em
logs por acidente — via tracebacks, `repr()` de payloads ou mensagens de erro de
driver. Em um sistema financeiro isso é um incidente de segurança, não um
detalhe de operação.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

# Padrões de dados sensíveis que nunca devem aparecer em log.
# Cada padrão preserva o nome do campo e substitui apenas o valor.
# A ordem importa: os padrões mais específicos (Bearer, JWT) precisam ser
# aplicados antes do padrão genérico de `chave=valor`, senão este último
# consome apenas a palavra "Bearer" e deixa o token exposto logo em seguida.
PADROES_DE_REDACAO: tuple[tuple[re.Pattern[str], str], ...] = (
    # Credenciais embutidas em URLs de conexão (postgres://user:senha@host).
    (re.compile(r"(?P<esquema>\w+://)[^:/\s@]+:[^@\s]+@"), r"\g<esquema><redigido>@"),
    # Cabeçalho Bearer com o token completo.
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]+"), "Bearer <redigido>"),
    # JWTs soltos no texto (três segmentos base64url separados por ponto).
    (
        re.compile(r"\beyJ[A-Za-z0-9_\-]*\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]*"),
        "<jwt-redigido>",
    ),
    # Hashes Argon2/bcrypt que porventura sejam impressos.
    (re.compile(r"\$(argon2[a-z]*|2[aby])\$[^\s\"']+"), "<hash-redigido>"),
    # Pares chave=valor e "chave": "valor" para campos sensíveis. A aspa de
    # fechamento da chave é opcional para cobrir tanto `senha=x` quanto
    # `"password": "x"`.
    (
        re.compile(
            r"(?i)\b(senha|password|passwd|secret|secret_key|api_key|apikey|"
            r"authorization|access_token|refresh_token|token|senha_nova|"
            r"senha_antiga|senha_hash)\b"
            r"(?P<sep>\"?\s*[=:]\s*\"?)"
            r"(?P<valor>[^\s,;&\"'})\]]+)"
        ),
        r"\1\g<sep><redigido>",
    ),
)


def redigir(texto: str) -> str:
    """Remove segredos conhecidos de um trecho de texto.

    Args:
        texto (str): O texto potencialmente contendo segredos.

    Returns:
        str: O texto com os valores sensíveis substituídos por marcadores.
    """
    resultado = texto
    for padrao, substituicao in PADROES_DE_REDACAO:
        resultado = padrao.sub(substituicao, resultado)
    return resultado


class FiltroDeRedacao(logging.Filter):
    """Filtro que aplica a redação de segredos a cada registro de log.

    Instalado no logger raiz para cobrir também bibliotecas de terceiros
    (SQLAlchemy, uvicorn, urllib3), que são fontes comuns de vazamento acidental.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Redige a mensagem já interpolada do registro.

        A interpolação é feita **antes** da redação, e o resultado substitui
        `msg` com `args` zerado. Redigir a string de formato e os argumentos
        separadamente corrompe o registro de duas maneiras:

        - redigir o formato pode apagar um `%s` (em `"senha=%s"`), deixando
          menos placeholders do que argumentos;
        - converter os argumentos para texto quebra formatações numéricas
          (`"%d" % "200"` levanta `TypeError`).

        Ambos os casos derrubam logs de bibliotecas de terceiros que usam
        formatação no estilo `%`, como httpx e uvicorn.

        Args:
            record (logging.LogRecord): O registro a ser tratado.

        Returns:
            bool: Sempre True — o registro é mantido, apenas sanitizado.
        """
        try:
            mensagem = record.getMessage()
        except (TypeError, ValueError):
            # Registro malformado pela origem: preserva o formato bruto em vez
            # de descartar o evento.
            mensagem = str(record.msg)

        record.msg = redigir(mensagem)
        record.args = None

        return True


class FormatadorJSON(logging.Formatter):
    """Formatador que serializa registros de log como uma linha JSON."""

    # Atributos padrão do LogRecord; qualquer outro é tratado como campo extra.
    _ATRIBUTOS_PADRAO = frozenset(
        {
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "module", "msecs",
            "message", "msg", "name", "pathname", "process", "processName",
            "relativeCreated", "stack_info", "thread", "threadName", "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        """Serializa o registro em JSON, incluindo campos extras.

        Args:
            record (logging.LogRecord): O registro a formatar.

        Returns:
            str: Uma linha JSON representando o evento.
        """
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=UTC
            ).isoformat(),
            "nivel": record.levelname,
            "logger": record.name,
            "mensagem": record.getMessage(),
        }

        for chave, valor in record.__dict__.items():
            if chave not in self._ATRIBUTOS_PADRAO and not chave.startswith("_"):
                payload[chave] = valor

        if record.exc_info:
            payload["excecao"] = redigir(self.formatException(record.exc_info))

        return json.dumps(payload, ensure_ascii=False, default=str)


def configurar_logging(nivel: str = "INFO") -> None:
    """Configura o logging estruturado global da aplicação.

    Substitui os handlers existentes por um único handler JSON em stdout e
    instala o filtro de redação no logger raiz.

    Args:
        nivel (str): Nível mínimo de log (ex.: 'INFO', 'DEBUG', 'WARNING').
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormatadorJSON())
    handler.addFilter(FiltroDeRedacao())

    raiz = logging.getLogger()
    raiz.handlers = [handler]
    raiz.setLevel(nivel.upper())

    # O logger de engine do SQLAlchemy imprime SQL com parâmetros; mantê-lo em
    # WARNING evita despejar valores de transações e hashes de senha no log.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # O access log do uvicorn duplica o log de requisição da aplicação.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def obter_logger(nome: str) -> logging.Logger:
    """Retorna um logger nomeado já coberto pela configuração global.

    Args:
        nome (str): Nome do logger, tipicamente `__name__`.

    Returns:
        logging.Logger: A instância do logger.
    """
    return logging.getLogger(nome)
