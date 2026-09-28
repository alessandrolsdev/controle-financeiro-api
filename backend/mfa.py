# Arquivo: backend/mfa.py
"""Autenticação em Duas Etapas (TOTP).

Implementa o segundo fator baseado em tempo (RFC 6238), compatível com Google
Authenticator, Authy, 1Password e afins, mais códigos de recuperação de uso
único para quando o usuário perde o dispositivo.

Decisões de engenharia:

- **Segredo cifrado em repouso.** O `mfa_secret` usa o tipo `TextoCifrado`:
  quem obtém uma cópia do banco não consegue gerar os códigos da vítima, o que
  anularia o segundo fator por completo.
- **Códigos de recuperação com hash Argon2.** Pelo mesmo motivo das senhas.
- **Janela de tolerância de ±1 intervalo.** Cobre relógios levemente
  dessincronizados sem ampliar a janela de força bruta de forma relevante —
  o rate limiting cuida do resto.
- **Consumo de código atômico.** Um código TOTP já usado não pode ser aceito de
  novo dentro do mesmo intervalo, o que impede replay de um código capturado.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from urllib.parse import quote

# Um segredo TOTP de 20 bytes (160 bits) é o tamanho recomendado pela RFC 4226.
TAMANHO_SEGREDO_BYTES = 20

# Parâmetros padrão do TOTP, iguais aos assumidos pelos aplicativos autenticadores.
DIGITOS = 6
INTERVALO_SEGUNDOS = 30

# Aceita o código do intervalo anterior e do seguinte, tolerando relógios com
# até 30 segundos de desvio.
JANELA_DE_TOLERANCIA = 1

# Quantidade e formato dos códigos de recuperação.
QUANTIDADE_DE_CODIGOS = 10
TAMANHO_DO_CODIGO = 10

# Alfabeto sem caracteres ambíguos (0/O, 1/I/L), para reduzir erro de digitação
# quando o usuário lê o código de um papel.
ALFABETO_DE_RECUPERACAO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def gerar_segredo() -> str:
    """Gera um novo segredo TOTP em base32.

    Returns:
        str: O segredo codificado em base32, sem preenchimento.
    """
    return base64.b32encode(os.urandom(TAMANHO_SEGREDO_BYTES)).decode("ascii").rstrip("=")


def _codigo_para_contador(segredo: str, contador: int) -> str:
    """Calcula o código HOTP para um contador específico.

    Args:
        segredo (str): O segredo em base32.
        contador (int): O contador (para TOTP, o número do intervalo).

    Returns:
        str: O código numérico com `DIGITOS` dígitos.
    """
    # O base32 do segredo pode ter sido armazenado sem preenchimento.
    preenchimento = "=" * (-len(segredo) % 8)
    chave = base64.b32decode(segredo + preenchimento, casefold=True)

    digest = hmac.new(chave, struct.pack(">Q", contador), hashlib.sha1).digest()

    # Truncamento dinâmico, conforme a RFC 4226 seção 5.3.
    deslocamento = digest[-1] & 0x0F
    trecho = struct.unpack(">I", digest[deslocamento:deslocamento + 4])[0] & 0x7FFFFFFF

    return str(trecho % (10 ** DIGITOS)).zfill(DIGITOS)


def gerar_codigo(segredo: str, momento: float | None = None) -> str:
    """Gera o código TOTP válido no instante informado.

    Args:
        segredo (str): O segredo em base32.
        momento (float | None): Timestamp Unix. Usa o horário atual se None.

    Returns:
        str: O código atual.
    """
    agora = momento if momento is not None else time.time()
    return _codigo_para_contador(segredo, int(agora // INTERVALO_SEGUNDOS))


def verificar_codigo(
    segredo: str, codigo: str, momento: float | None = None
) -> int | None:
    """Verifica um código TOTP dentro da janela de tolerância.

    A comparação usa `hmac.compare_digest` para não vazar, pelo tempo de
    execução, quantos dígitos iniciais estavam corretos.

    Args:
        segredo (str): O segredo em base32.
        codigo (str): O código informado pelo usuário.
        momento (float | None): Timestamp Unix. Usa o horário atual se None.

    Returns:
        int | None: O contador em que o código foi aceito, ou None se inválido.
        O contador é devolvido para que a aplicação possa registrá-lo e recusar
        o mesmo código em uma segunda tentativa (proteção contra replay).
    """
    normalizado = codigo.strip().replace(" ", "")

    if not normalizado.isdigit() or len(normalizado) != DIGITOS:
        return None

    agora = momento if momento is not None else time.time()
    contador_atual = int(agora // INTERVALO_SEGUNDOS)

    for desvio in range(-JANELA_DE_TOLERANCIA, JANELA_DE_TOLERANCIA + 1):
        contador = contador_atual + desvio
        if hmac.compare_digest(_codigo_para_contador(segredo, contador), normalizado):
            return contador

    return None


def montar_uri_de_provisionamento(
    segredo: str, nome_usuario: str, emissor: str = "NOMAD Controle Financeiro"
) -> str:
    """Monta a URI `otpauth://` lida pelos aplicativos autenticadores.

    O frontend transforma essa URI em QR Code. Ela contém o segredo, então
    trafega apenas na resposta do enrollment, para o próprio usuário, e nunca
    é registrada em log.

    Args:
        segredo (str): O segredo em base32.
        nome_usuario (str): Identificação da conta no aplicativo.
        emissor (str): Nome da aplicação exibido no autenticador.

    Returns:
        str: A URI de provisionamento.
    """
    rotulo = quote(f"{emissor}:{nome_usuario}", safe="")
    parametros = (
        f"secret={segredo}"
        f"&issuer={quote(emissor, safe='')}"
        f"&algorithm=SHA1"
        f"&digits={DIGITOS}"
        f"&period={INTERVALO_SEGUNDOS}"
    )
    return f"otpauth://totp/{rotulo}?{parametros}"


def gerar_codigos_de_recuperacao() -> list[str]:
    """Gera um lote de códigos de recuperação de uso único.

    Returns:
        list[str]: Códigos em texto claro, exibidos ao usuário uma única vez.
    """
    codigos = []

    for _ in range(QUANTIDADE_DE_CODIGOS):
        bruto = "".join(
            secrets.choice(ALFABETO_DE_RECUPERACAO) for _ in range(TAMANHO_DO_CODIGO)
        )
        # Hífen no meio para facilitar a leitura e a digitação.
        codigos.append(f"{bruto[:5]}-{bruto[5:]}")

    return codigos


def normalizar_codigo_de_recuperacao(codigo: str) -> str:
    """Normaliza um código de recuperação para comparação.

    Torna a verificação tolerante a maiúsculas/minúsculas, espaços e à presença
    ou ausência do hífen — variações comuns quando o usuário digita o código.

    Args:
        codigo (str): O código informado.

    Returns:
        str: O código normalizado.
    """
    return codigo.strip().upper().replace("-", "").replace(" ", "")
