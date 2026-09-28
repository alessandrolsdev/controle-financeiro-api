# Arquivo: backend/core/middleware.py
"""Middlewares de Segurança e Observabilidade.

Reúne os middlewares aplicados a todas as requisições:

- `MiddlewareDeHeadersDeSeguranca`: adiciona os cabeçalhos de defesa do
  navegador (HSTS, CSP, anti-clickjacking, política de referrer).
- `MiddlewareDeTamanhoDeCorpo`: rejeita corpos de requisição acima do limite,
  evitando exaustão de memória.
- `MiddlewareDeLogDeRequisicao`: emite um log estruturado por requisição, com
  um ID de correlação, sem registrar corpos nem cabeçalhos sensíveis.
"""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from .config import settings
from .logging import obter_logger

logger = obter_logger(__name__)

# A API serve apenas JSON e não renderiza HTML, então a política pode ser
# máxima: nada pode ser carregado, nenhum script pode rodar, e a página não
# pode ser embutida em um frame.
CSP_DA_API = (
    "default-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'none'; "
    "form-action 'none'; "
    "sandbox"
)

# A documentação interativa (/docs) precisa carregar o bundle do Swagger UI a
# partir de uma CDN, portanto recebe uma política própria e mais permissiva.
CSP_DOCS = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' https://fastapi.tiangolo.com data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'"
)

CAMINHOS_DE_DOCUMENTACAO = ("/docs", "/redoc", "/openapi.json")


class MiddlewareDeHeadersDeSeguranca(BaseHTTPMiddleware):
    """Adiciona cabeçalhos de segurança do navegador a todas as respostas."""

    async def dispatch(self, request: Request, call_next):
        """Processa a requisição e enriquece a resposta com headers de defesa.

        Args:
            request (Request): A requisição recebida.
            call_next: O próximo manipulador da cadeia.

        Returns:
            Response: A resposta com os cabeçalhos de segurança aplicados.
        """
        resposta: Response = await call_next(request)

        e_documentacao = request.url.path in CAMINHOS_DE_DOCUMENTACAO
        resposta.headers["Content-Security-Policy"] = (
            CSP_DOCS if e_documentacao else CSP_DA_API
        )

        # Impede que o navegador adivinhe o tipo de conteúdo (defesa contra
        # XSS por confusão de MIME type).
        resposta.headers["X-Content-Type-Options"] = "nosniff"

        # Defesa em profundidade contra clickjacking, para navegadores antigos
        # que não honram `frame-ancestors`.
        resposta.headers["X-Frame-Options"] = "DENY"

        # Não vaza a URL da API (que contém IDs de recursos) para terceiros.
        resposta.headers["Referrer-Policy"] = "no-referrer"

        # Nenhum recurso de dispositivo é necessário para uma API JSON.
        resposta.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )

        # Respostas com dados financeiros nunca devem ser armazenadas em cache
        # compartilhado, proxy ou disco.
        resposta.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        resposta.headers["Pragma"] = "no-cache"

        # Isola a janela de origens cruzadas (protege contra Spectre e vazamento
        # de referências entre janelas).
        resposta.headers["Cross-Origin-Resource-Policy"] = "same-site"
        resposta.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        if settings.is_production:
            # Só faz sentido sob HTTPS; ativar em dev quebraria o localhost.
            resposta.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        # O servidor não deve anunciar sua identidade e versão.
        if "server" in resposta.headers:
            del resposta.headers["server"]

        return resposta


class MiddlewareDeTamanhoDeCorpo(BaseHTTPMiddleware):
    """Rejeita requisições cujo corpo excede o limite configurado."""

    def __init__(self, app: ASGIApp, tamanho_maximo: int) -> None:
        """Inicializa o middleware.

        Args:
            app (ASGIApp): A aplicação ASGI encapsulada.
            tamanho_maximo (int): Tamanho máximo do corpo em bytes.
        """
        super().__init__(app)
        self._tamanho_maximo = tamanho_maximo

    async def dispatch(self, request: Request, call_next):
        """Valida o `Content-Length` antes de processar a requisição.

        Args:
            request (Request): A requisição recebida.
            call_next: O próximo manipulador da cadeia.

        Returns:
            Response: 413 se o corpo for grande demais, ou a resposta normal.
        """
        content_length = request.headers.get("content-length")

        if content_length is not None:
            try:
                if int(content_length) > self._tamanho_maximo:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Corpo da requisição excede o limite permitido."},
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Cabeçalho Content-Length inválido."},
                )

        return await call_next(request)


class MiddlewareDeLogDeRequisicao(BaseHTTPMiddleware):
    """Registra um evento estruturado por requisição, com ID de correlação.

    Deliberadamente **não** registra corpo, query string com valores nem o
    cabeçalho `Authorization` — apenas metadados necessários para auditoria e
    diagnóstico.
    """

    async def dispatch(self, request: Request, call_next):
        """Mede e registra a requisição.

        Args:
            request (Request): A requisição recebida.
            call_next: O próximo manipulador da cadeia.

        Returns:
            Response: A resposta, com o cabeçalho `X-Request-ID`.
        """
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        inicio = time.perf_counter()

        try:
            resposta: Response = await call_next(request)
        except Exception:
            duracao_ms = (time.perf_counter() - inicio) * 1000
            logger.exception(
                "Erro não tratado ao processar requisição",
                extra={
                    "request_id": request_id,
                    "metodo": request.method,
                    "caminho": request.url.path,
                    "duracao_ms": round(duracao_ms, 2),
                    "ip_cliente": obter_ip_do_cliente(request),
                },
            )
            raise

        duracao_ms = (time.perf_counter() - inicio) * 1000
        resposta.headers["X-Request-ID"] = request_id

        logger.info(
            "Requisição processada",
            extra={
                "request_id": request_id,
                "metodo": request.method,
                "caminho": request.url.path,
                "status": resposta.status_code,
                "duracao_ms": round(duracao_ms, 2),
                "ip_cliente": obter_ip_do_cliente(request),
            },
        )

        return resposta


def obter_ip_do_cliente(request: Request) -> str:
    """Determina o IP de origem da requisição.

    Em produção a aplicação roda atrás de um proxy reverso (Render, nginx), que
    preenche `X-Forwarded-For`. Confiamos apenas na primeira entrada e somente
    quando o cabeçalho está presente — este valor é usado para rate limiting e
    para a trilha de auditoria, nunca para autorização.

    Args:
        request (Request): A requisição recebida.

    Returns:
        str: O endereço IP do cliente, ou 'desconhecido'.
    """
    encaminhado = request.headers.get("x-forwarded-for")
    if encaminhado:
        return encaminhado.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "desconhecido"
