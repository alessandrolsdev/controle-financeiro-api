# Arquivo: backend/core/config.py
"""Módulo de Configuração Central da Aplicação.

Carrega e **valida** todas as variáveis de ambiente necessárias para a execução
do backend. A validação é deliberadamente rígida: em ambiente de produção a
aplicação se recusa a subir com configuração insegura, em vez de degradar
silenciosamente para um padrão frágil.

Regras de segurança aplicadas aqui:
- `SECRET_KEY` precisa ter entropia mínima e não pode ser uma chave conhecida
  publicamente (a chave de exemplo da documentação do FastAPI, que chegou a ser
  publicada no README deste repositório, é rejeitada explicitamente).
- Em produção, `DATABASE_URL` é obrigatória (sem fallback silencioso para SQLite)
  e a lista de origens de CORS precisa ser explícita (sem curingas).
- Algoritmos de assinatura JWT são restritos a uma allowlist.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# `NoDecode` desliga a desserialização JSON automática que o pydantic-settings
# aplica a campos de tipo complexo lidos do ambiente. Sem isso, um valor como
# `CORS_ORIGINS=https://a.com,https://b.com` falharia antes de chegar ao
# validador que sabe interpretar listas separadas por vírgula.
ListaDeTexto = Annotated[list[str], NoDecode]

# Define o caminho absoluto para a pasta raiz do projeto
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_PATH = os.path.join(ROOT_DIR, ".env")

# Algoritmos de assinatura aceitos. `none` e algoritmos assimétricos mal
# configurados são a raiz das falhas de confusão de algoritmo em JWT.
ALGORITMOS_PERMITIDOS = frozenset({"HS256", "HS384", "HS512"})

# Comprimento mínimo da SECRET_KEY em caracteres.
TAMANHO_MINIMO_SECRET_KEY = 32

# Hashes SHA-256 de segredos sabidamente comprometidos/públicos.
# Guardamos o hash (e não o valor) para não reintroduzir o segredo no código.
#
# - O primeiro é a chave de exemplo da documentação oficial do FastAPI
#   ("09d25e09...e8d3e7"), que foi publicada no README deste repositório entre
#   o commit inicial e o commit 9211ad0. Qualquer implantação que tenha seguido
#   aquelas instruções possui uma chave de assinatura JWT de conhecimento
#   público — ou seja, tokens forjáveis por qualquer pessoa.
SEGREDOS_COMPROMETIDOS = frozenset(
    {
        "570dad43de1af4c925f92c16a68a50936da42b7dd6fdeb24850507a1199aac89",
    }
)

# Valores placeholder que jamais devem chegar a um ambiente real.
PLACEHOLDERS_PROIBIDOS = frozenset(
    {
        "change-me",
        "changeme",
        "secret",
        "secretkey",
        "secret_key",
        "sua_chave_secreta_aqui",
        "sua_chave_secreta_super_segura_aqui",
        "test",
        "testing",
        "dev",
        "development",
        "password",
        "string",
    }
)


def _hash_segredo(valor: str) -> str:
    """Calcula o SHA-256 de um segredo para comparação com a denylist.

    Args:
        valor (str): O segredo em texto plano.

    Returns:
        str: O digest hexadecimal SHA-256.
    """
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


class Settings(BaseSettings):
    """Configurações globais da aplicação carregadas de variáveis de ambiente.

    Attributes:
        ENVIRONMENT: Ambiente de execução. Controla o rigor das validações.
        SECRET_KEY: Chave usada para assinar tokens JWT.
        ALGORITHM: Algoritmo de assinatura JWT (restrito a HS256/384/512).
        ACCESS_TOKEN_EXPIRE_MINUTES: Validade do token de acesso em minutos.
        JWT_ISSUER: Claim `iss` esperado nos tokens.
        JWT_AUDIENCE: Claim `aud` esperado nos tokens.
        DATABASE_URL: URL de conexão com o banco. Obrigatória em produção.
        DB_POOL_SIZE: Tamanho do pool de conexões.
        DB_MAX_OVERFLOW: Conexões extras permitidas além do pool.
        DB_POOL_RECYCLE_SECONDS: Idade máxima de uma conexão antes de reciclar.
        CORS_ORIGINS: Allowlist explícita de origens do navegador.
        RATE_LIMIT_LOGIN: Tentativas de login permitidas por janela.
        RATE_LIMIT_LOGIN_WINDOW_SECONDS: Duração da janela de rate limit do login.
        RATE_LIMIT_SIGNUP: Cadastros permitidos por janela e por IP.
        RATE_LIMIT_SIGNUP_WINDOW_SECONDS: Duração da janela de rate limit do cadastro.
        REDIS_URL: Backend compartilhado de rate limiting (necessário com múltiplas instâncias).
        LOG_LEVEL: Nível de log da aplicação.
        DOCS_ENABLED: Se a documentação interativa (/docs) fica exposta.
        TRUSTED_HOSTS: Allowlist de cabeçalhos Host aceitos.
        MAX_REQUEST_BODY_BYTES: Tamanho máximo aceito de corpo de requisição.
    """

    # --- Ambiente ---
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # --- Configurações de Segurança ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=1440)
    JWT_ISSUER: str = "nomad-controle-financeiro"
    JWT_AUDIENCE: str = "nomad-app"

    # --- Configurações do Banco de Dados ---
    DATABASE_URL: str | None = None
    DB_POOL_SIZE: int = Field(default=5, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0, le=100)
    DB_POOL_RECYCLE_SECONDS: int = Field(default=1800, ge=60)

    # --- CORS ---
    # Allowlist explícita. Sem curinga: com `allow_credentials=True` um curinga
    # de subdomínio (ex.: `*.vercel.app`) permite que qualquer pessoa publique
    # um site e leia os dados financeiros da vítima autenticada.
    CORS_ORIGINS: ListaDeTexto = Field(default_factory=list)

    # --- Rate limiting ---
    RATE_LIMIT_LOGIN: int = Field(default=5, ge=1)
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = Field(default=300, ge=10)
    RATE_LIMIT_SIGNUP: int = Field(default=5, ge=1)
    RATE_LIMIT_SIGNUP_WINDOW_SECONDS: int = Field(default=3600, ge=10)
    REDIS_URL: str | None = None

    # --- Observabilidade ---
    LOG_LEVEL: str = "INFO"

    # --- Superfície exposta ---
    DOCS_ENABLED: bool = True
    TRUSTED_HOSTS: ListaDeTexto = Field(default_factory=lambda: ["*"])
    MAX_REQUEST_BODY_BYTES: int = Field(default=1_048_576, ge=1024)

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Validadores ---

    @field_validator("CORS_ORIGINS", "TRUSTED_HOSTS", mode="before")
    @classmethod
    def _dividir_lista(cls, valor: object) -> object:
        """Aceita listas separadas por vírgula vindas de variáveis de ambiente.

        Args:
            valor: Valor bruto lido do ambiente.

        Returns:
            A lista já separada, ou o valor original quando não for string.
        """
        if isinstance(valor, str):
            valor = valor.strip()
            # Aceita também o formato JSON (ex.: '["https://a.com"]').
            if valor.startswith("["):
                import json

                return json.loads(valor)
            return [item.strip() for item in valor.split(",") if item.strip()]
        return valor

    @field_validator("ALGORITHM")
    @classmethod
    def _validar_algoritmo(cls, valor: str) -> str:
        """Restringe o algoritmo JWT a uma allowlist de algoritmos simétricos.

        Args:
            valor (str): O algoritmo configurado.

        Raises:
            ValueError: Se o algoritmo não estiver na allowlist.

        Returns:
            str: O algoritmo validado.
        """
        if valor not in ALGORITMOS_PERMITIDOS:
            raise ValueError(
                f"ALGORITHM '{valor}' não é permitido. "
                f"Use um de: {sorted(ALGORITMOS_PERMITIDOS)}."
            )
        return valor

    @field_validator("SECRET_KEY")
    @classmethod
    def _validar_secret_key(cls, valor: str) -> str:
        """Garante que a SECRET_KEY tem entropia suficiente e não é pública.

        Args:
            valor (str): A chave configurada.

        Raises:
            ValueError: Se a chave for curta, um placeholder, tiver baixa
                variedade de caracteres ou constar na denylist de segredos
                comprometidos.

        Returns:
            str: A chave validada.
        """
        chave = valor.strip()

        if len(chave) < TAMANHO_MINIMO_SECRET_KEY:
            raise ValueError(
                f"SECRET_KEY precisa ter ao menos {TAMANHO_MINIMO_SECRET_KEY} "
                "caracteres. Gere uma com: "
                'python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )

        if chave.lower() in PLACEHOLDERS_PROIBIDOS:
            raise ValueError(
                "SECRET_KEY é um valor placeholder conhecido. Gere uma chave real."
            )

        if _hash_segredo(chave) in SEGREDOS_COMPROMETIDOS:
            raise ValueError(
                "SECRET_KEY consta na lista de segredos comprometidos "
                "(esta chave é pública: aparece na documentação do FastAPI e no "
                "histórico Git deste repositório). Rotacione imediatamente — veja "
                "SECURITY.md."
            )

        # Uma chave com pouquíssimos caracteres distintos (ex.: 'aaaa...') passa
        # no teste de comprimento mas não tem entropia real.
        if len(set(chave)) < 12:
            raise ValueError(
                "SECRET_KEY tem entropia insuficiente (poucos caracteres distintos). "
                'Gere uma com: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )

        return chave

    @model_validator(mode="after")
    def _validar_coerencia_de_producao(self) -> Settings:
        """Aplica as exigências extras válidas apenas em produção.

        Raises:
            ValueError: Se a configuração de produção estiver insegura.

        Returns:
            Settings: A própria instância validada.
        """
        if self.ENVIRONMENT != "production":
            return self

        if not self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL é obrigatória em produção. O fallback para SQLite "
                "local não é aceitável para dados financeiros."
            )

        if self.DATABASE_URL.startswith("sqlite"):
            raise ValueError(
                "SQLite não é suportado em produção. Use PostgreSQL."
            )

        if not self.CORS_ORIGINS:
            raise ValueError(
                "CORS_ORIGINS precisa listar explicitamente as origens do frontend "
                "em produção (ex.: CORS_ORIGINS=https://app.exemplo.com)."
            )

        for origem in self.CORS_ORIGINS:
            if "*" in origem:
                raise ValueError(
                    f"Origem CORS '{origem}' contém curinga. Com credenciais "
                    "habilitadas isso permite que qualquer site sob esse domínio "
                    "leia os dados do usuário autenticado. Liste as origens uma a uma."
                )
            partes = urlparse(origem)
            if partes.scheme != "https":
                raise ValueError(
                    f"Origem CORS '{origem}' precisa usar HTTPS em produção."
                )
            if not partes.netloc:
                raise ValueError(
                    f"Origem CORS '{origem}' é inválida. Use o formato "
                    "https://host[:porta], sem caminho."
                )
            if partes.path not in ("", "/"):
                raise ValueError(
                    f"Origem CORS '{origem}' não deve conter caminho."
                )

        if self.TRUSTED_HOSTS == ["*"]:
            raise ValueError(
                "TRUSTED_HOSTS precisa ser explícito em produção para impedir "
                "ataques de Host header poisoning."
            )

        return self

    # --- Propriedades derivadas ---

    @property
    def is_production(self) -> bool:
        """Indica se a aplicação está rodando em produção.

        Returns:
            bool: True quando ENVIRONMENT == 'production'.
        """
        return self.ENVIRONMENT == "production"

    @property
    def cookies_seguros(self) -> bool:
        """Indica se cookies devem ter a flag `Secure`.

        Returns:
            bool: True fora de desenvolvimento.
        """
        return self.ENVIRONMENT != "development"


def _mascarar(valor: str | None) -> str:
    """Mascara um valor sensível para exibição segura em logs.

    Args:
        valor: O valor a mascarar.

    Returns:
        str: Uma representação sem o conteúdo sensível.
    """
    if not valor:
        return "<vazio>"
    return f"<oculto:{len(valor)} chars>"


def descrever_configuracao(config: Settings) -> dict[str, object]:
    """Monta um resumo da configuração seguro para registrar em log.

    Nenhum segredo é incluído: `SECRET_KEY` é mascarada e a `DATABASE_URL` tem
    usuário e senha removidos.

    Args:
        config (Settings): A configuração carregada.

    Returns:
        dict[str, object]: Resumo sem dados sensíveis.
    """
    banco = "<não configurado>"
    if config.DATABASE_URL:
        # Remove credenciais embutidas na URL de conexão.
        banco = re.sub(r"//[^/@]*@", "//<credenciais-ocultas>@", config.DATABASE_URL)

    return {
        "environment": config.ENVIRONMENT,
        "database": banco,
        "secret_key": _mascarar(config.SECRET_KEY),
        "algorithm": config.ALGORITHM,
        "token_expira_em_minutos": config.ACCESS_TOKEN_EXPIRE_MINUTES,
        "cors_origins": config.CORS_ORIGINS,
        "docs_habilitado": config.DOCS_ENABLED,
        "rate_limit_backend": "redis" if config.REDIS_URL else "memoria-local",
    }


# Cria uma instância única das configurações.
settings = Settings()
