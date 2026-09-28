# Arquivo: backend/core/rate_limit.py
"""Módulo de Limitação de Taxa (Rate Limiting).

Implementa uma janela deslizante para conter ataques de força bruta contra
autenticação e abuso de endpoints de cadastro.

Dois backends são suportados:
- **Redis** (recomendado em produção): o contador é compartilhado entre todas as
  instâncias/workers da aplicação.
- **Memória local** (fallback): funciona por processo. Com múltiplos workers do
  gunicorn o limite efetivo é multiplicado pelo número de workers, portanto o
  backend Redis deve ser configurado em qualquer implantação com mais de um
  processo. A aplicação registra um aviso explícito quando isso acontece.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from .config import settings
from .logging import obter_logger

logger = obter_logger(__name__)


@dataclass(frozen=True)
class ResultadoRateLimit:
    """Resultado de uma verificação de rate limit.

    Attributes:
        permitido (bool): Se a requisição pode prosseguir.
        restantes (int): Quantas requisições ainda cabem na janela atual.
        retry_after (int): Segundos até a janela liberar, quando bloqueado.
    """

    permitido: bool
    restantes: int
    retry_after: int


class LimitadorEmMemoria:
    """Limitador de janela deslizante mantido na memória do processo.

    Thread-safe. Usado como fallback quando `REDIS_URL` não está configurada.
    """

    def __init__(self) -> None:
        """Inicializa as estruturas internas do limitador."""
        self._acessos: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self._ultima_limpeza = time.monotonic()

    def verificar(self, chave: str, limite: int, janela: int) -> ResultadoRateLimit:
        """Registra um acesso e informa se ele deve ser permitido.

        Args:
            chave (str): Identificador do balde (ex.: 'login:203.0.113.4').
            limite (int): Máximo de acessos permitidos na janela.
            janela (int): Duração da janela em segundos.

        Returns:
            ResultadoRateLimit: Veredito da verificação.
        """
        agora = time.monotonic()
        corte = agora - janela

        with self._lock:
            self._limpar_expirados(agora, janela)

            registros = [t for t in self._acessos.get(chave, []) if t > corte]

            if len(registros) >= limite:
                mais_antigo = min(registros)
                retry_after = max(1, int(janela - (agora - mais_antigo)) + 1)
                self._acessos[chave] = registros
                return ResultadoRateLimit(False, 0, retry_after)

            registros.append(agora)
            self._acessos[chave] = registros
            return ResultadoRateLimit(True, limite - len(registros), 0)

    def _limpar_expirados(self, agora: float, janela: int) -> None:
        """Remove baldes inteiramente expirados para limitar o uso de memória.

        A varredura ocorre no máximo uma vez por minuto para não penalizar o
        caminho quente. Deve ser chamada com o lock já adquirido.

        Args:
            agora (float): Timestamp monotônico atual.
            janela (int): Duração da janela em segundos.
        """
        if agora - self._ultima_limpeza < 60:
            return

        corte = agora - janela
        self._acessos = {
            chave: registros
            for chave, registros in self._acessos.items()
            if any(t > corte for t in registros)
        }
        self._ultima_limpeza = agora


class LimitadorRedis:
    """Limitador de janela deslizante compartilhado via Redis.

    Usa um sorted set por chave, podado a cada verificação. Todas as operações
    são executadas em um pipeline para reduzir round-trips.
    """

    def __init__(self, url: str) -> None:
        """Conecta ao Redis.

        Args:
            url (str): URL de conexão do Redis.

        Raises:
            ImportError: Se o pacote `redis` não estiver instalado.
        """
        import redis  # Importado sob demanda: é uma dependência opcional.

        self._cliente = redis.Redis.from_url(url, decode_responses=True)

    def verificar(self, chave: str, limite: int, janela: int) -> ResultadoRateLimit:
        """Registra um acesso e informa se ele deve ser permitido.

        Args:
            chave (str): Identificador do balde.
            limite (int): Máximo de acessos permitidos na janela.
            janela (int): Duração da janela em segundos.

        Returns:
            ResultadoRateLimit: Veredito da verificação.
        """
        agora = time.time()
        corte = agora - janela
        chave_redis = f"ratelimit:{chave}"

        pipe = self._cliente.pipeline()
        pipe.zremrangebyscore(chave_redis, 0, corte)
        pipe.zcard(chave_redis)
        pipe.zadd(chave_redis, {f"{agora}:{time.monotonic_ns()}": agora})
        pipe.expire(chave_redis, janela + 1)
        _, quantidade, _, _ = pipe.execute()

        if quantidade >= limite:
            # O acesso recém-adicionado não deve contar quando já bloqueado.
            self._cliente.zremrangebyrank(chave_redis, -1, -1)
            return ResultadoRateLimit(False, 0, janela)

        return ResultadoRateLimit(True, limite - quantidade - 1, 0)


@dataclass
class _EstadoLimitador:
    """Guarda a instância única do backend de rate limiting.

    Attributes:
        backend: A implementação ativa (Redis ou memória).
    """

    backend: object | None = field(default=None)


_estado = _EstadoLimitador()


def obter_limitador() -> LimitadorEmMemoria | LimitadorRedis:
    """Retorna o backend de rate limiting configurado.

    Tenta usar Redis quando `REDIS_URL` está definida e cai para o limitador em
    memória se a conexão falhar, registrando um aviso.

    Returns:
        LimitadorEmMemoria | LimitadorRedis: O backend ativo.
    """
    if _estado.backend is not None:
        return _estado.backend  # type: ignore[return-value]

    if settings.REDIS_URL:
        try:
            _estado.backend = LimitadorRedis(settings.REDIS_URL)
            logger.info("Rate limiting usando backend Redis compartilhado.")
            return _estado.backend  # type: ignore[return-value]
        except Exception as erro:  # noqa: BLE001 - degradação controlada
            logger.error(
                "Falha ao conectar ao Redis para rate limiting; "
                "usando fallback em memória (limite por processo).",
                extra={"erro": str(erro)},
            )

    if settings.is_production:
        logger.warning(
            "Rate limiting em memória em produção: o limite é aplicado por "
            "processo. Configure REDIS_URL para um limite global consistente."
        )

    _estado.backend = LimitadorEmMemoria()
    return _estado.backend


def verificar_limite(chave: str, limite: int, janela: int) -> ResultadoRateLimit:
    """Verifica o rate limit para uma chave usando o backend ativo.

    Args:
        chave (str): Identificador do balde.
        limite (int): Máximo de acessos na janela.
        janela (int): Duração da janela em segundos.

    Returns:
        ResultadoRateLimit: Veredito da verificação.
    """
    return obter_limitador().verificar(chave, limite, janela)  # type: ignore[union-attr]


def resetar_limitador() -> None:
    """Descarta o backend ativo. Usado para isolar casos de teste."""
    _estado.backend = None
