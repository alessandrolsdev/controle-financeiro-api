# Arquivo: backend/core/cripto.py
"""Criptografia de Campos Sensíveis em Repouso.

Adiciona uma camada de proteção **da aplicação** sobre os dados pessoais, além
da criptografia de disco oferecida pelo provedor de banco. As duas resolvem
ameaças diferentes:

- A criptografia do provedor protege contra alguém que leve o disco embora.
- Esta camada protege contra quem obtém acesso de leitura ao banco — um backup
  vazado, uma réplica mal configurada, um dump em ticket de suporte ou uma
  injeção de SQL. Nesses cenários a criptografia de disco já foi aplicada e
  descriptografada; os dados aparecem em texto claro.

Decisões de engenharia:

- **AES-256-GCM**: cifra autenticada. Adulterar o texto cifrado no banco produz
  erro de verificação, não um valor silenciosamente diferente.
- **Chave derivada por HKDF** a partir de `ENCRYPTION_KEY`, com `info` distinto
  por finalidade. A chave de cifragem e a de índice cego são independentes,
  então vazar uma não compromete a outra.
- **Índice cego (HMAC-SHA256)** para o e-mail: permite manter a restrição de
  unicidade e a busca por igualdade sem guardar o valor em claro.
- **Prefixo de versão** no texto cifrado (`v1:`), para permitir rotação de chave
  no futuro sem ambiguidade sobre o formato.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import String, TypeDecorator

from .config import settings

# Marca o formato do texto cifrado. Uma futura rotação de chave usaria 'v2:',
# permitindo decifrar os dois formatos durante a transição.
PREFIXO_VERSAO = "v1:"

# O GCM exige um nonce único por mensagem. 96 bits é o tamanho recomendado.
TAMANHO_NONCE = 12

# Rótulos HKDF que separam as chaves derivadas por finalidade.
_INFO_CIFRAGEM = b"nomad-controle-financeiro/cifragem-de-campo/v1"
_INFO_INDICE_CEGO = b"nomad-controle-financeiro/indice-cego/v1"


def _derivar(info: bytes) -> bytes:
    """Deriva uma chave de 32 bytes para uma finalidade específica.

    Args:
        info (bytes): Rótulo que separa esta chave das demais.

    Returns:
        bytes: A chave derivada.
    """
    material = (settings.ENCRYPTION_KEY or settings.SECRET_KEY).encode("utf-8")

    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        # `salt=None` é aceitável aqui: o material de entrada já é um segredo de
        # alta entropia, e o `info` garante a separação entre finalidades.
        salt=None,
        info=info,
    ).derive(material)


class _Chaves:
    """Cache das chaves derivadas.

    A derivação HKDF é barata, mas roda a cada leitura e escrita de campo; o
    cache evita repeti-la milhares de vezes ao serializar uma listagem.
    """

    def __init__(self) -> None:
        """Inicializa o cache vazio."""
        self._cifragem: bytes | None = None
        self._indice: bytes | None = None

    @property
    def cifragem(self) -> bytes:
        """Chave usada para cifrar e decifrar campos.

        Returns:
            bytes: A chave de 32 bytes.
        """
        if self._cifragem is None:
            self._cifragem = _derivar(_INFO_CIFRAGEM)
        return self._cifragem

    @property
    def indice(self) -> bytes:
        """Chave usada para calcular índices cegos.

        Returns:
            bytes: A chave de 32 bytes.
        """
        if self._indice is None:
            self._indice = _derivar(_INFO_INDICE_CEGO)
        return self._indice

    def limpar(self) -> None:
        """Descarta as chaves em cache. Usado em testes de rotação."""
        self._cifragem = None
        self._indice = None


_chaves = _Chaves()


def cifrar(texto: str) -> str:
    """Cifra um texto com AES-256-GCM.

    Args:
        texto (str): O valor em claro.

    Returns:
        str: O texto cifrado, no formato `v1:<base64(nonce || cifra || tag)>`.
    """
    nonce = os.urandom(TAMANHO_NONCE)
    cifra = AESGCM(_chaves.cifragem).encrypt(nonce, texto.encode("utf-8"), None)
    return PREFIXO_VERSAO + base64.b64encode(nonce + cifra).decode("ascii")


def decifrar(valor: str) -> str:
    """Decifra um valor produzido por :func:`cifrar`.

    Valores sem o prefixo de versão são devolvidos como estão. Isso permite que
    a aplicação leia registros gravados antes da introdução da criptografia,
    enquanto a migração de dados ainda não rodou.

    Args:
        valor (str): O texto cifrado ou um valor legado em claro.

    Raises:
        ValueError: Se o texto cifrado estiver corrompido ou tiver sido
            adulterado (a autenticação do GCM falha).

    Returns:
        str: O valor em claro.
    """
    if not valor.startswith(PREFIXO_VERSAO):
        return valor

    bruto = base64.b64decode(valor[len(PREFIXO_VERSAO):])
    nonce, cifra = bruto[:TAMANHO_NONCE], bruto[TAMANHO_NONCE:]

    return AESGCM(_chaves.cifragem).decrypt(nonce, cifra, None).decode("utf-8")


def indice_cego(valor: str) -> str:
    """Calcula um índice determinístico para busca e unicidade.

    O valor é normalizado (minúsculas, sem espaços nas bordas) antes do HMAC,
    de modo que `Alice@Exemplo.com` e `alice@exemplo.com` colidam — que é o
    comportamento esperado para e-mail.

    O HMAC usa chave secreta, e não um hash puro: sem a chave, um atacante com
    o banco em mãos não consegue confirmar se um endereço conhecido está
    cadastrado por força bruta sobre o conjunto de e-mails plausíveis.

    Args:
        valor (str): O valor em claro.

    Returns:
        str: O digest hexadecimal do HMAC-SHA256.
    """
    normalizado = valor.strip().lower().encode("utf-8")
    return hmac.new(_chaves.indice, normalizado, hashlib.sha256).hexdigest()


class TextoCifrado(TypeDecorator):
    """Tipo SQLAlchemy que cifra o valor ao gravar e decifra ao ler.

    A cifragem fica invisível para a camada CRUD e para os schemas: o modelo
    continua expondo `str`. Como consequência, uma consulta `WHERE campo = ...`
    sobre uma coluna deste tipo **não** funciona — cada gravação usa um nonce
    diferente, então o mesmo valor em claro produz textos cifrados distintos.
    Para campos que precisam ser pesquisáveis, use um índice cego em paralelo.

    Attributes:
        impl: Tipo de coluna subjacente.
        cache_ok: Indica que o tipo é seguro para o cache de compilação.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        """Cifra o valor no caminho de escrita.

        Args:
            value: O valor em claro (ou None).
            dialect: O dialeto do banco em uso.

        Returns:
            str | None: O texto cifrado, ou None.
        """
        if value is None:
            return None
        return cifrar(str(value))

    def process_result_value(self, value: Any, dialect: Any) -> str | None:
        """Decifra o valor no caminho de leitura.

        Args:
            value: O texto cifrado lido do banco (ou None).
            dialect: O dialeto do banco em uso.

        Returns:
            str | None: O valor em claro, ou None.
        """
        if value is None:
            return None
        return decifrar(value)
