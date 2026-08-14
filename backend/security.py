# Arquivo: backend/security.py
"""Módulo de Segurança e Autenticação.

Implementa as funções críticas de segurança da aplicação: hashing de senhas com
Argon2id e emissão/validação de tokens JWT.

Decisões de engenharia relevantes:

- **PyJWT em vez de python-jose.** O `python-jose` está praticamente sem
  manutenção e acumula vulnerabilidades conhecidas de confusão de algoritmo
  (CVE-2024-33663) e negação de serviço por "JWT bomb" (CVE-2024-33664). O
  PyJWT é mantido ativamente e valida o algoritmo de forma estrita.
- **Claims completos.** Todo token carrega `iss`, `aud`, `iat`, `nbf`, `exp`,
  `jti` e `ver`. O algoritmo aceito na decodificação é fixado por allowlist,
  fechando a porta para tokens `alg: none` ou trocados para outra família.
- **Revogação por versão.** O claim `ver` espelha o campo `token_version` do
  usuário. Trocar a senha ou encerrar todas as sessões incrementa esse contador,
  invalidando imediatamente todos os tokens já emitidos — algo que um JWT sem
  estado não oferece por padrão.
- **Argon2id explícito.** Parâmetros de custo definidos no código, e não
  herdados de um padrão que pode mudar entre versões da biblioteca.
"""

from __future__ import annotations

import unicodedata
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from fastapi import HTTPException, status

from .core.config import settings
from .core.logging import obter_logger

logger = obter_logger(__name__)

# --- Configurações de Segurança ---
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# --- Política de Senha ---
# O mínimo de 12 caracteres segue a recomendação do NIST SP 800-63B para
# segredos memorizados sem exigência de rotação periódica.
TAMANHO_MINIMO_SENHA = 12

# Argon2 processa a senha inteira; sem um teto, uma senha de vários megabytes
# vira um vetor de negação de serviço por consumo de CPU e memória.
TAMANHO_MAXIMO_SENHA = 1024

# Senhas triviais mais comuns em vazamentos, normalizadas em minúsculas.
SENHAS_PROIBIDAS = frozenset(
    {
        "123456789012", "senha123456", "password1234", "qwertyuiop12",
        "111111111111", "123123123123", "abcdefghijkl", "senhasenha12",
        "administrador", "controlefinanceiro", "nomadfinanceiro",
    }
)

# --- Contexto de Senha (Argon2id) ---
# Parâmetros alinhados ao perfil "segundo recomendado" da RFC 9106:
# 64 MiB de memória, 3 iterações, paralelismo 4.
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

# Hash descartável usado para igualar o tempo de resposta quando o usuário não
# existe. Sem isso, o login responde visivelmente mais rápido para usuários
# inexistentes, permitindo enumerar contas válidas por medição de tempo.
_HASH_DUMMY = _hasher.hash("senha-inexistente-para-equalizar-tempo-de-resposta")


# --- Funções de Senha ---


def normalizar_senha(senha: str) -> str:
    """Normaliza a senha em NFKC antes de qualquer operação criptográfica.

    Garante que a mesma senha digitada em teclados ou sistemas operacionais
    diferentes (com acentos compostos de formas distintas) produza o mesmo hash.

    Args:
        senha (str): A senha em texto plano.

    Returns:
        str: A senha normalizada.
    """
    return unicodedata.normalize("NFKC", senha)


def validar_forca_da_senha(senha: str) -> list[str]:
    """Avalia se a senha atende à política mínima da aplicação.

    Args:
        senha (str): A senha em texto plano.

    Returns:
        list[str]: Lista de problemas encontrados. Vazia se a senha for válida.
    """
    problemas: list[str] = []
    normalizada = normalizar_senha(senha)

    if len(normalizada) < TAMANHO_MINIMO_SENHA:
        problemas.append(
            f"A senha precisa ter ao menos {TAMANHO_MINIMO_SENHA} caracteres."
        )

    if len(normalizada.encode("utf-8")) > TAMANHO_MAXIMO_SENHA:
        problemas.append(
            f"A senha excede o limite de {TAMANHO_MAXIMO_SENHA} bytes."
        )

    if normalizada.lower() in SENHAS_PROIBIDAS:
        problemas.append("Esta senha é comum demais. Escolha outra.")

    if len(set(normalizada)) < 5:
        problemas.append("A senha tem pouca variedade de caracteres.")

    # Sequências repetidas do mesmo caractere ('aaaaaaaaaaaa') passariam nos
    # testes acima de comprimento mas não agregam entropia.
    if normalizada and normalizada == normalizada[0] * len(normalizada):
        problemas.append("A senha não pode ser um único caractere repetido.")

    return problemas


def verificar_senha(senha_plana: str, senha_hashed: str) -> bool:
    """Verifica se a senha fornecida corresponde ao hash armazenado.

    A comparação é feita pela biblioteca Argon2, que é resistente a ataques de
    tempo. Qualquer erro de verificação resulta em `False` — nunca em exceção
    propagada, para não diferenciar "hash corrompido" de "senha errada".

    Args:
        senha_plana (str): A senha em texto plano fornecida pelo usuário.
        senha_hashed (str): O hash da senha armazenado no banco de dados.

    Returns:
        bool: True se as senhas conferem, False caso contrário.
    """
    if not senha_hashed:
        return False

    try:
        return _hasher.verify(senha_hashed, normalizar_senha(senha_plana))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def consumir_tempo_de_verificacao() -> None:
    """Executa uma verificação descartável de senha.

    Chamada no fluxo de login quando o usuário informado não existe, para que o
    tempo de resposta seja indistinguível do caso "usuário existe, senha
    errada". Sem essa equalização, o endpoint de login vira um oráculo de
    enumeração de contas.
    """
    try:
        _hasher.verify(_HASH_DUMMY, "senha-arbitraria-que-nao-confere")
    except Exception:  # noqa: BLE001,S110 - nosec B110
        # O descarte da exceção é intencional: esta função existe apenas para
        # consumir o mesmo tempo de CPU de uma verificação real. O resultado é
        # irrelevante por definição — tratá-lo criaria justamente a diferença
        # de comportamento que se quer eliminar.
        pass


def get_hash_da_senha(senha: str) -> str:
    """Gera um hash seguro para a senha fornecida usando Argon2id.

    Args:
        senha (str): A senha em texto plano.

    Raises:
        ValueError: Se a senha ultrapassar o limite de tamanho.

    Returns:
        str: O hash da senha gerado.
    """
    normalizada = normalizar_senha(senha)

    if len(normalizada.encode("utf-8")) > TAMANHO_MAXIMO_SENHA:
        raise ValueError(
            f"A senha excede o limite de {TAMANHO_MAXIMO_SENHA} bytes."
        )

    try:
        return _hasher.hash(normalizada)
    except HashingError as erro:
        logger.error("Falha ao gerar hash de senha", extra={"erro": str(erro)})
        raise


def precisa_reidratar_hash(senha_hashed: str) -> bool:
    """Indica se o hash foi gerado com parâmetros de custo desatualizados.

    Permite migrar hashes antigos de forma transparente no próximo login bem
    sucedido, sem exigir que o usuário troque a senha.

    Args:
        senha_hashed (str): O hash armazenado.

    Returns:
        bool: True se o hash deve ser regerado com os parâmetros atuais.
    """
    try:
        return _hasher.check_needs_rehash(senha_hashed)
    except (InvalidHashError, ValueError):
        # Hash em formato desconhecido (ex.: bcrypt legado) também deve migrar.
        return True


# --- Funções de Token (JWT) ---


def criar_token_de_acesso(
    nome_usuario: str,
    usuario_id: int,
    token_version: int,
    expires_delta: timedelta | None = None,
) -> str:
    """Cria um token de acesso JWT assinado com o conjunto completo de claims.

    Args:
        nome_usuario (str): Nome de usuário, gravado no claim `sub`.
        usuario_id (int): ID numérico do usuário, gravado no claim `uid`.
        token_version (int): Versão atual das credenciais, no claim `ver`.
        expires_delta (Optional[timedelta]): Validade personalizada. Se None,
            usa `ACCESS_TOKEN_EXPIRE_MINUTES`.

    Returns:
        str: O token JWT codificado.
    """
    agora = datetime.now(UTC)
    validade = expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": nome_usuario,
        "uid": usuario_id,
        "ver": token_version,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": agora,
        "nbf": agora,
        "exp": agora + validade,
        # Identificador único do token: permite auditoria e revogação pontual.
        "jti": str(uuid.uuid4()),
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str, credentials_exception: HTTPException) -> dict[str, Any]:
    """Valida a assinatura e os claims de um token JWT.

    O algoritmo é fixado por allowlist e `iss`/`aud` são verificados, de modo que
    um token assinado para outro serviço — ou com `alg` alterado — é rejeitado.

    Args:
        token (str): O token JWT a ser validado.
        credentials_exception (HTTPException): Exceção lançada em caso de falha.

    Raises:
        credentials_exception: Se o token for inválido, expirado ou incompleto.

    Returns:
        dict[str, Any]: O payload decodificado.
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={
                "require": ["exp", "iat", "nbf", "sub", "iss", "aud", "jti"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )
    # `from None` corta a cadeia de exceções de propósito: encadear a causa
    # original faria o motivo exato da rejeição (expirado, assinatura inválida,
    # audience errada) aparecer no traceback. O motivo é registrado em log
    # estruturado, onde só a operação o vê — nunca na resposta ao cliente.
    except jwt.ExpiredSignatureError:
        logger.info("Token rejeitado: expirado")
        raise credentials_exception from None
    except jwt.InvalidTokenError as erro:
        # Cobre assinatura inválida, algoritmo divergente, claims ausentes,
        # issuer/audience errados e payload malformado.
        logger.warning("Token rejeitado", extra={"motivo": type(erro).__name__})
        raise credentials_exception from None

    if not isinstance(payload.get("sub"), str) or not payload["sub"]:
        raise credentials_exception

    if not isinstance(payload.get("ver"), int):
        raise credentials_exception

    return payload


def gerar_chave_de_idempotencia() -> str:
    """Gera uma chave de idempotência no formato usado pela API.

    Returns:
        str: Um UUID4 em formato canônico.
    """
    return str(uuid.uuid4())


def criar_excecao_de_credenciais() -> HTTPException:
    """Cria a exceção padrão de falha de autenticação.

    A mensagem é deliberadamente genérica: distinguir "token expirado" de
    "assinatura inválida" entrega informação útil a um atacante.

    Returns:
        HTTPException: Exceção 401 com o cabeçalho WWW-Authenticate.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
