# Arquivo: backend/sessoes.py
"""Gestão de Sessão: Cookies, CSRF e Rotação de Refresh Tokens.

Substitui o armazenamento do token em `localStorage`, que era legível por
qualquer JavaScript executando na página — inclusive o injetado por um XSS.

Modelo adotado:

- **Cookies `httpOnly`.** O token de acesso e o refresh token viajam em cookies
  que o JavaScript não consegue ler. Um XSS pode fazer requisições em nome do
  usuário enquanto a página está aberta, mas não consegue **exfiltrar** a
  credencial para uso posterior — que é a diferença entre um incidente contido
  e uma conta comprometida em definitivo.
- **`SameSite=Strict` + double-submit CSRF.** Cookies enviados automaticamente
  pelo navegador reintroduzem o risco de CSRF. `SameSite` resolve na maioria
  dos navegadores; o token CSRF em cookie legível, ecoado no cabeçalho
  `X-CSRF-Token`, cobre o resto. Um site atacante consegue *disparar* a
  requisição, mas não consegue *ler* o cookie para preencher o cabeçalho.
- **Bearer continua aceito.** Clientes que não são navegadores (scripts, apps
  nativos, integrações) seguem usando `Authorization: Bearer`. Como não há
  cookie enviado automaticamente nesse caminho, o CSRF não se aplica a ele.
- **Rotação de refresh token com detecção de reuso.** Cada uso invalida o token
  e emite outro. Se um token já usado reaparece, uma cópia vazou: a família
  inteira é revogada.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, security
from .core.config import settings
from .core.logging import obter_logger
from .models import agora_utc, como_utc

logger = obter_logger(__name__)

# --- Nomes dos cookies ---
# O prefixo `__Host-` é uma instrução ao navegador: só aceite este cookie se
# vier por HTTPS, sem atributo Domain e com Path=/. Isso impede que um
# subdomínio comprometido sobrescreva o cookie de sessão do domínio principal.
# Fora de produção o prefixo é omitido, já que exige HTTPS.
_PREFIXO = "__Host-" if settings.is_production and not settings.COOKIE_DOMAIN else ""

COOKIE_ACESSO = f"{_PREFIXO}nomad_access"
COOKIE_REFRESH = f"{_PREFIXO}nomad_refresh"
COOKIE_CSRF = f"{_PREFIXO}nomad_csrf"

CABECALHO_CSRF = "X-CSRF-Token"

# O refresh token só é enviado ao endpoint que o consome. Restringir o caminho
# reduz a exposição: ele não acompanha cada requisição de dados.
CAMINHO_REFRESH = "/auth/refresh"

# Métodos que alteram estado e portanto exigem verificação de CSRF.
METODOS_INSEGUROS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def gerar_token_csrf() -> str:
    """Gera um token CSRF aleatório.

    Returns:
        str: Token em formato URL-safe.
    """
    return secrets.token_urlsafe(32)


def definir_cookies_de_sessao(
    resposta: Response,
    token_de_acesso: str,
    refresh_token: str,
    token_csrf: str,
) -> None:
    """Grava os cookies de sessão na resposta.

    Args:
        resposta (Response): A resposta HTTP em construção.
        token_de_acesso (str): O JWT de acesso.
        refresh_token (str): O refresh token opaco.
        token_csrf (str): O token CSRF a ser ecoado pelo cliente.
    """
    comum = {
        "secure": settings.cookies_seguros,
        "samesite": settings.COOKIE_SAMESITE,
        "domain": settings.COOKIE_DOMAIN,
    }

    resposta.set_cookie(
        COOKIE_ACESSO,
        token_de_acesso,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        path="/",
        **comum,
    )

    resposta.set_cookie(
        COOKIE_REFRESH,
        refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        # Enviado apenas ao endpoint de renovação.
        path=CAMINHO_REFRESH,
        **comum,
    )

    # Deliberadamente legível por JavaScript: o frontend precisa lê-lo para
    # ecoá-lo no cabeçalho. É o mecanismo de double-submit — a segurança vem de
    # a origem atacante não conseguir ler cookies de outro site, não de o token
    # ser secreto para a própria página.
    resposta.set_cookie(
        COOKIE_CSRF,
        token_csrf,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=False,
        path="/",
        **comum,
    )


def limpar_cookies_de_sessao(resposta: Response) -> None:
    """Remove os cookies de sessão da resposta.

    Args:
        resposta (Response): A resposta HTTP em construção.
    """
    comum = {
        "secure": settings.cookies_seguros,
        "samesite": settings.COOKIE_SAMESITE,
        "domain": settings.COOKIE_DOMAIN,
    }

    resposta.delete_cookie(COOKIE_ACESSO, path="/", httponly=True, **comum)
    resposta.delete_cookie(
        COOKIE_REFRESH, path=CAMINHO_REFRESH, httponly=True, **comum
    )
    resposta.delete_cookie(COOKIE_CSRF, path="/", httponly=False, **comum)


def extrair_token_de_acesso(request: Request) -> str | None:
    """Obtém o token de acesso do cookie ou do cabeçalho Authorization.

    O cookie tem precedência: é o caminho usado pelo navegador. O cabeçalho
    atende clientes que não são navegadores.

    Args:
        request (Request): A requisição atual.

    Returns:
        str | None: O token, se presente.
    """
    do_cookie = request.cookies.get(COOKIE_ACESSO)
    if do_cookie:
        return do_cookie

    autorizacao = request.headers.get("authorization", "")
    if autorizacao.lower().startswith("bearer "):
        return autorizacao[7:].strip() or None

    return None


def requisicao_usa_cookie(request: Request) -> bool:
    """Indica se a autenticação desta requisição veio de cookie.

    Só o caminho por cookie precisa de verificação de CSRF: o navegador envia
    cookies automaticamente, mas nunca envia um cabeçalho `Authorization` por
    conta própria.

    Args:
        request (Request): A requisição atual.

    Returns:
        bool: True se há cookie de acesso presente.
    """
    return COOKIE_ACESSO in request.cookies


def csrf_valido(request: Request) -> bool:
    """Verifica a correspondência entre o cookie e o cabeçalho CSRF.

    Args:
        request (Request): A requisição atual.

    Returns:
        bool: True se o cabeçalho corresponde ao cookie.
    """
    do_cookie = request.cookies.get(COOKIE_CSRF)
    do_cabecalho = request.headers.get(CABECALHO_CSRF)

    if not do_cookie or not do_cabecalho:
        return False

    # Comparação em tempo constante, por hábito: não há segredo do servidor
    # aqui, mas o custo é nulo e evita depender dessa análise no futuro.
    return secrets.compare_digest(do_cookie, do_cabecalho)


# --- Refresh Tokens ---


def emitir_refresh_token(
    db: Session,
    usuario: models.Usuario,
    familia_id: str | None = None,
    ip_cliente: str | None = None,
    user_agent: str | None = None,
) -> str:
    """Emite um refresh token e registra seu hash no banco.

    Args:
        db (Session): Sessão do banco de dados.
        usuario (models.Usuario): Dono do token.
        familia_id (str | None): Família da cadeia de rotação. Um valor novo
            inicia uma sessão; reutilizar o existente continua a cadeia.
        ip_cliente (str | None): IP de origem.
        user_agent (str | None): Cliente que solicitou o token.

    Returns:
        str: O refresh token em texto claro, para envio ao cliente.
    """
    token = security.gerar_refresh_token()

    registro = models.RefreshToken(
        token_hash=security.hash_de_refresh_token(token),
        familia_id=familia_id or secrets.token_hex(18),
        usuario_id=usuario.id,
        expira_em=agora_utc() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ip_cliente=ip_cliente,
        user_agent=(user_agent or "")[:255] or None,
    )
    db.add(registro)

    return token


def revogar_familia(
    db: Session, usuario_id: int, familia_id: str, motivo: str
) -> int:
    """Revoga todos os refresh tokens de uma família.

    Args:
        db (Session): Sessão do banco de dados.
        usuario_id (int): Dono dos tokens.
        familia_id (str): A família a revogar.
        motivo (str): Registro do porquê da revogação.

    Returns:
        int: Quantidade de tokens revogados.
    """
    tokens = db.scalars(
        select(models.RefreshToken).where(
            models.RefreshToken.usuario_id == usuario_id,
            models.RefreshToken.familia_id == familia_id,
            models.RefreshToken.revogado_em.is_(None),
        )
    ).all()

    agora = agora_utc()
    for token in tokens:
        token.revogado_em = agora
        token.motivo_revogacao = motivo

    return len(tokens)


def revogar_todas_as_sessoes(db: Session, usuario_id: int, motivo: str) -> int:
    """Revoga todos os refresh tokens ativos de um usuário.

    Args:
        db (Session): Sessão do banco de dados.
        usuario_id (int): Dono dos tokens.
        motivo (str): Registro do porquê da revogação.

    Returns:
        int: Quantidade de tokens revogados.
    """
    tokens = db.scalars(
        select(models.RefreshToken).where(
            models.RefreshToken.usuario_id == usuario_id,
            models.RefreshToken.revogado_em.is_(None),
        )
    ).all()

    agora = agora_utc()
    for token in tokens:
        token.revogado_em = agora
        token.motivo_revogacao = motivo

    return len(tokens)


class ResultadoDeRotacao:
    """Desfecho de uma tentativa de renovar a sessão.

    Attributes:
        sucesso (bool): Se um novo par de tokens foi emitido.
        usuario (models.Usuario | None): O dono da sessão, quando reconhecido.
        novo_refresh_token (str | None): O token que substitui o apresentado.
        reuso_detectado (bool): Se o token apresentado já havia sido usado —
            indício de que uma cópia vazou.
    """

    __slots__ = ("sucesso", "usuario", "novo_refresh_token", "reuso_detectado")

    def __init__(
        self,
        sucesso: bool,
        usuario: models.Usuario | None = None,
        novo_refresh_token: str | None = None,
        reuso_detectado: bool = False,
    ) -> None:
        """Inicializa o resultado.

        Args:
            sucesso (bool): Se a rotação foi bem-sucedida.
            usuario (models.Usuario | None): O dono da sessão.
            novo_refresh_token (str | None): O novo token emitido.
            reuso_detectado (bool): Se houve reuso de um token já consumido.
        """
        self.sucesso = sucesso
        self.usuario = usuario
        self.novo_refresh_token = novo_refresh_token
        self.reuso_detectado = reuso_detectado


def rotacionar_refresh_token(
    db: Session,
    token_apresentado: str,
    ip_cliente: str | None = None,
    user_agent: str | None = None,
) -> ResultadoDeRotacao:
    """Troca um refresh token válido por um novo, detectando reuso.

    O token apresentado é marcado como usado e um sucessor é emitido na mesma
    família. Se o token já tinha sido usado, o mais provável é que ele tenha
    sido capturado e replicado — o cliente legítimo já teria recebido o
    sucessor. Nesse caso a família inteira cai, encerrando as duas sessões.

    Args:
        db (Session): Sessão do banco de dados.
        token_apresentado (str): O refresh token recebido do cliente.
        ip_cliente (str | None): IP de origem.
        user_agent (str | None): Cliente que solicitou a renovação.

    Returns:
        ResultadoDeRotacao: O desfecho da tentativa.
    """
    registro = db.scalar(
        select(models.RefreshToken).where(
            models.RefreshToken.token_hash
            == security.hash_de_refresh_token(token_apresentado)
        )
    )

    if registro is None:
        return ResultadoDeRotacao(sucesso=False)

    if registro.usado_em is not None:
        # Reuso: o token legítimo já foi trocado. Derruba a família inteira.
        revogados = revogar_familia(
            db, registro.usuario_id, registro.familia_id, "reuso_detectado"
        )
        logger.warning(
            "Reuso de refresh token detectado; família revogada",
            extra={
                "usuario_id": registro.usuario_id,
                "familia_id": registro.familia_id,
                "tokens_revogados": revogados,
                "ip_cliente": ip_cliente,
            },
        )
        return ResultadoDeRotacao(sucesso=False, reuso_detectado=True)

    if registro.revogado_em is not None or como_utc(registro.expira_em) <= agora_utc():
        return ResultadoDeRotacao(sucesso=False)

    usuario = db.get(models.Usuario, registro.usuario_id)
    if usuario is None:
        return ResultadoDeRotacao(sucesso=False)

    registro.usado_em = agora_utc()

    novo_token = emitir_refresh_token(
        db,
        usuario,
        familia_id=registro.familia_id,
        ip_cliente=ip_cliente,
        user_agent=user_agent,
    )

    return ResultadoDeRotacao(
        sucesso=True, usuario=usuario, novo_refresh_token=novo_token
    )


def limpar_tokens_expirados(db: Session) -> int:
    """Remove refresh tokens expirados há mais de 30 dias.

    A retenção após a expiração é intencional: um token expirado que reaparece
    ainda é sinal útil de vazamento, e a trilha de auditoria pode referenciá-lo.

    Args:
        db (Session): Sessão do banco de dados.

    Returns:
        int: Quantidade de registros removidos.
    """
    corte = agora_utc() - timedelta(days=30)

    antigos = db.scalars(
        select(models.RefreshToken).where(models.RefreshToken.expira_em < corte)
    ).all()

    for token in antigos:
        db.delete(token)

    return len(antigos)
