# Arquivo: tests/test_autenticacao.py
"""Testes de Autenticação, Tokens e Política de Senha."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from conftest import SENHA_VALIDA, autenticar, cabecalho, criar_conta

from backend import security
from backend.core.config import settings


def test_login_com_credenciais_validas(cliente):
    """O login bem-sucedido devolve um token e sua validade."""
    criar_conta(cliente, "alice")

    resposta = cliente.post(
        "/token", data={"username": "alice", "password": SENHA_VALIDA}
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["token_type"] == "bearer"
    assert corpo["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_mensagem_de_erro_nao_revela_se_usuario_existe(cliente):
    """Usuário inexistente e senha errada produzem a mesma resposta.

    Uma mensagem diferente para cada caso permite enumerar contas válidas.
    """
    criar_conta(cliente, "alice")

    inexistente = cliente.post(
        "/token", data={"username": "fantasma", "password": "QualquerCoisa#123"}
    )
    senha_errada = cliente.post(
        "/token", data={"username": "alice", "password": "SenhaErrada#4567"}
    )

    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.json() == senha_errada.json()


def test_endpoints_protegidos_exigem_token(cliente):
    """Sem token, os endpoints de dados respondem 401."""
    for metodo, caminho in [
        ("get", "/usuarios/me"),
        ("get", "/transacoes/"),
        ("get", "/categorias/"),
    ]:
        resposta = getattr(cliente, metodo)(caminho)
        assert resposta.status_code == 401, caminho


def test_token_com_assinatura_invalida_e_rejeitado(cliente, usuario_com_token):
    """Um token assinado com outra chave não é aceito."""
    _, token = usuario_com_token
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )

    token_forjado = jwt.encode(payload, "chave-do-atacante", algorithm="HS256")

    resposta = cliente.get("/usuarios/me", headers=cabecalho(token_forjado))
    assert resposta.status_code == 401


def test_token_sem_assinatura_e_rejeitado(cliente, usuario_com_token):
    """Um token com `alg: none` é recusado.

    Esta é a falha clássica de confusão de algoritmo; o decodificador fixa o
    algoritmo por allowlist justamente para bloqueá-la.
    """
    _, token = usuario_com_token
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )

    token_sem_assinatura = jwt.encode(payload, key="", algorithm="none")

    resposta = cliente.get("/usuarios/me", headers=cabecalho(token_sem_assinatura))
    assert resposta.status_code == 401


def test_token_expirado_e_rejeitado(cliente, usuario_com_token):
    """Um token cuja validade passou não é aceito."""
    usuario, _ = usuario_com_token

    agora = datetime.now(UTC)
    token_expirado = jwt.encode(
        {
            "sub": usuario["nome_usuario"],
            "uid": usuario["id"],
            "ver": 1,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "iat": agora - timedelta(hours=2),
            "nbf": agora - timedelta(hours=2),
            "exp": agora - timedelta(hours=1),
            "jti": "teste",
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    resposta = cliente.get("/usuarios/me", headers=cabecalho(token_expirado))
    assert resposta.status_code == 401


def test_token_de_outro_emissor_e_rejeitado(cliente, usuario_com_token):
    """Um token válido emitido para outro serviço não vale aqui."""
    usuario, _ = usuario_com_token

    agora = datetime.now(UTC)
    token_de_terceiro = jwt.encode(
        {
            "sub": usuario["nome_usuario"],
            "uid": usuario["id"],
            "ver": 1,
            "iss": "outro-servico",
            "aud": "outra-audiencia",
            "iat": agora,
            "nbf": agora,
            "exp": agora + timedelta(hours=1),
            "jti": "teste",
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    resposta = cliente.get("/usuarios/me", headers=cabecalho(token_de_terceiro))
    assert resposta.status_code == 401


def test_troca_de_senha_revoga_tokens_existentes(cliente, usuario_com_token):
    """Após trocar a senha, o token antigo deixa de funcionar imediatamente."""
    _, token = usuario_com_token

    assert cliente.get("/usuarios/me", headers=cabecalho(token)).status_code == 200

    nova_senha = "OutraSenhaForte#2026"
    resposta = cliente.post(
        "/usuarios/mudar-senha",
        json={"senha_antiga": SENHA_VALIDA, "senha_nova": nova_senha},
        headers=cabecalho(token),
    )
    assert resposta.status_code == 200

    # O token emitido antes da troca não vale mais.
    assert cliente.get("/usuarios/me", headers=cabecalho(token)).status_code == 401

    # E a nova senha funciona.
    novo_token = autenticar(cliente, "alice", nova_senha)
    assert cliente.get("/usuarios/me", headers=cabecalho(novo_token)).status_code == 200


def test_revogar_sessoes_invalida_token(cliente, usuario_com_token):
    """O endpoint de revogação encerra as sessões sem trocar a senha."""
    _, token = usuario_com_token

    resposta = cliente.post(
        "/usuarios/me/revogar-sessoes", headers=cabecalho(token)
    )
    assert resposta.status_code == 200

    assert cliente.get("/usuarios/me", headers=cabecalho(token)).status_code == 401


@pytest.mark.parametrize(
    "senha",
    [
        "curta",              # abaixo do mínimo
        "aaaaaaaaaaaaaaaa",   # caractere único repetido
        "123456789012",       # senha comum
    ],
)
def test_senha_fraca_e_rejeitada_no_cadastro(cliente, senha):
    """Senhas que não atendem à política não criam conta.

    Args:
        senha (str): A senha fraca sob teste.
    """
    resposta = cliente.post(
        "/usuarios/", json={"nome_usuario": "novo_usuario", "senha": senha}
    )
    assert resposta.status_code in (400, 422)


def test_senha_nao_e_refletida_em_erro_de_validacao(cliente):
    """A resposta de erro não devolve a senha enviada.

    O tratador padrão do FastAPI ecoa o valor recebido no campo `input`, o que
    faria a senha aparecer na resposta e em qualquer log de resposta no caminho.
    """
    senha_secreta = "curta"
    resposta = cliente.post(
        "/usuarios/", json={"nome_usuario": "u", "senha": senha_secreta}
    )

    assert senha_secreta not in resposta.text


def test_hash_de_senha_nunca_aparece_na_resposta(cliente, usuario_com_token):
    """O perfil não expõe `senha_hash` nem `token_version`."""
    _, token = usuario_com_token

    corpo = cliente.get("/usuarios/me", headers=cabecalho(token)).json()

    assert "senha_hash" not in corpo
    assert "token_version" not in corpo


def test_atualizacao_de_perfil_rejeita_campos_extras(cliente, usuario_com_token):
    """Enviar campos fora do schema é recusado (defesa contra mass assignment)."""
    _, token = usuario_com_token

    resposta = cliente.put(
        "/usuarios/me",
        json={"nome_completo": "Alice", "token_version": 999, "senha_hash": "x"},
        headers=cabecalho(token),
    )
    assert resposta.status_code == 422


def test_rate_limit_bloqueia_forca_bruta(cliente):
    """Após várias tentativas falhas, o login passa a responder 429."""
    criar_conta(cliente, "alvo")

    respostas = [
        cliente.post(
            "/token", data={"username": "alvo", "password": f"ErradaN{i}#2026"}
        ).status_code
        for i in range(settings.RATE_LIMIT_LOGIN + 3)
    ]

    assert 429 in respostas


def test_avatar_url_com_esquema_perigoso_e_rejeitada(cliente, usuario_com_token):
    """URLs `javascript:` no avatar são recusadas (XSS armazenado)."""
    _, token = usuario_com_token

    resposta = cliente.put(
        "/usuarios/me",
        json={"avatar_url": "javascript:alert(document.cookie)"},
        headers=cabecalho(token),
    )
    assert resposta.status_code == 422


def test_forca_de_senha_aceita_senha_boa():
    """A política aprova uma senha longa e variada."""
    assert security.validar_forca_da_senha("SenhaForte#2026!nomad") == []


def test_verificacao_de_senha_nao_lanca_com_hash_invalido():
    """Um hash corrompido resulta em False, não em exceção."""
    assert security.verificar_senha("qualquer", "nao-e-um-hash") is False
    assert security.verificar_senha("qualquer", "") is False
