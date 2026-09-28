# Arquivo: tests/test_sessoes_e_mfa.py
"""Testes de Sessão em Cookie, CSRF, Refresh Token e Segundo Fator."""

from __future__ import annotations

from conftest import SENHA_VALIDA, cabecalho, criar_conta
from fastapi.testclient import TestClient

from backend import crud, mfa, sessoes
from backend.database import SessionLocal

PERIODO = {"data_inicio": "2026-03-01", "data_fim": "2026-03-31"}


# --- Cookies e CSRF ---


def test_tokens_nao_aparecem_no_corpo_da_resposta(cliente):
    """O login não devolve credenciais no JSON, apenas em cookies httpOnly."""
    criar_conta(cliente, "alice")

    resposta = cliente.post(
        "/auth/login", data={"username": "alice", "password": SENHA_VALIDA}
    )

    corpo = resposta.text
    assert "access_token" not in corpo
    assert "refresh_token" not in corpo


def test_cookies_de_sessao_sao_httponly(cliente):
    """Os cookies de acesso e renovação não são legíveis por JavaScript."""
    criar_conta(cliente, "alice")
    resposta = cliente.post(
        "/auth/login", data={"username": "alice", "password": SENHA_VALIDA}
    )

    definidos = resposta.headers.get_list("set-cookie")

    acesso = next(c for c in definidos if c.startswith(sessoes.COOKIE_ACESSO))
    refresh = next(c for c in definidos if c.startswith(sessoes.COOKIE_REFRESH))

    assert "httponly" in acesso.lower()
    assert "httponly" in refresh.lower()

    # O cookie CSRF, ao contrário, precisa ser legível: é o frontend que o
    # ecoa no cabeçalho para completar o double-submit.
    csrf = next(c for c in definidos if c.startswith(sessoes.COOKIE_CSRF))
    assert "httponly" not in csrf.lower()


def test_escrita_sem_token_csrf_e_bloqueada(cliente, usuario_com_token):
    """Uma requisição por cookie sem o cabeçalho CSRF é recusada."""
    _, csrf = usuario_com_token

    resposta = cliente.post(
        "/categorias/",
        json={"nome": "Sem CSRF", "tipo": "Gasto", "cor": "#FF0000"},
    )
    assert resposta.status_code == 403


def test_escrita_com_token_csrf_errado_e_bloqueada(cliente, usuario_com_token):
    """Um cabeçalho CSRF que não corresponde ao cookie é recusado."""
    _, csrf = usuario_com_token

    resposta = cliente.post(
        "/categorias/",
        json={"nome": "CSRF errado", "tipo": "Gasto", "cor": "#FF0000"},
        headers={"X-CSRF-Token": "valor-que-o-atacante-chutou"},
    )
    assert resposta.status_code == 403


def test_leitura_nao_exige_token_csrf(cliente, usuario_com_token):
    """Métodos que não alteram estado dispensam a verificação de CSRF."""
    assert cliente.get("/usuarios/me").status_code == 200


def test_bearer_dispensa_csrf(cliente):
    """Clientes de API autenticados por Bearer não passam pela checagem CSRF.

    O navegador nunca envia `Authorization` sozinho, então esse caminho não é
    atacável por CSRF — exigir o cabeçalho ali só quebraria integrações.
    """
    from backend import security

    usuario = criar_conta(cliente, "alice")
    token = security.criar_token_de_acesso(
        nome_usuario=usuario["nome_usuario"],
        usuario_id=usuario["id"],
        token_version=1,
    )

    cliente.cookies.clear()
    resposta = cliente.post(
        "/categorias/",
        json={"nome": "Via API", "tipo": "Gasto", "cor": "#FF0000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resposta.status_code == 201


def test_logout_limpa_cookies_e_revoga_sessao(cliente, usuario_com_token):
    """O logout encerra a sessão no servidor, não só no navegador."""
    _, csrf = usuario_com_token

    assert cliente.get("/usuarios/me").status_code == 200

    assert cliente.post("/auth/logout", headers=cabecalho(csrf)).status_code == 200

    # O refresh token revogado não renova mais nada.
    assert cliente.post("/auth/refresh").status_code == 401


# --- Refresh token ---


def test_refresh_emite_nova_sessao(cliente, usuario_com_token):
    """A renovação devolve um novo par de tokens e mantém o acesso."""
    resposta = cliente.post("/auth/refresh")

    assert resposta.status_code == 200
    assert resposta.json()["csrf_token"]
    assert cliente.get("/usuarios/me").status_code == 200


def test_refresh_token_e_rotacionado(cliente, usuario_com_token):
    """Cada renovação substitui o refresh token anterior."""
    antes = cliente.cookies.get(sessoes.COOKIE_REFRESH)

    cliente.post("/auth/refresh")

    depois = cliente.cookies.get(sessoes.COOKIE_REFRESH)
    assert depois != antes


def test_reuso_de_refresh_token_revoga_a_familia(cliente, usuario_com_token):
    """Reapresentar um refresh token já usado derruba a sessão inteira.

    É o sinal de que uma cópia do token vazou: o cliente legítimo já teria
    recebido o sucessor. Derrubar a família expulsa atacante e vítima, que é o
    desfecho seguro.
    """
    token_antigo = cliente.cookies.get(sessoes.COOKIE_REFRESH)

    # Uso legítimo: rotaciona.
    assert cliente.post("/auth/refresh").status_code == 200

    # O atacante apresenta a cópia que capturou.
    atacante = TestClient(cliente.app)
    atacante.cookies.set(sessoes.COOKIE_REFRESH, token_antigo)
    assert atacante.post("/auth/refresh").status_code == 401

    # E a sessão legítima também cai.
    assert cliente.post("/auth/refresh").status_code == 401


def test_troca_de_senha_revoga_refresh_tokens(cliente, usuario_com_token):
    """Trocar a senha invalida também a renovação, não só o acesso."""
    _, csrf = usuario_com_token

    resposta = cliente.post(
        "/usuarios/mudar-senha",
        json={"senha_antiga": SENHA_VALIDA, "senha_nova": "NovaSenhaForte#2026"},
        headers=cabecalho(csrf),
    )
    assert resposta.status_code == 200

    assert cliente.post("/auth/refresh").status_code == 401


# --- Segundo fator (MFA) ---


def _ativar_mfa(cliente, csrf) -> tuple[str, list[str]]:
    """Ativa o segundo fator e devolve o segredo e os códigos de recuperação.

    Args:
        cliente: Cliente HTTP de teste.
        csrf (str): Token CSRF da sessão.

    Returns:
        tuple[str, list[str]]: O segredo TOTP e os códigos de recuperação.
    """
    inicio = cliente.post(
        "/usuarios/me/mfa/iniciar", headers=cabecalho(csrf)
    ).json()
    segredo = inicio["segredo"]

    resposta = cliente.post(
        "/usuarios/me/mfa/confirmar",
        json={"codigo": mfa.gerar_codigo(segredo)},
        headers=cabecalho(csrf),
    )
    assert resposta.status_code == 200, resposta.text

    return segredo, resposta.json()["codigos"]


def test_ativacao_de_mfa_exige_codigo_valido(cliente, usuario_com_token):
    """O segundo fator só é ativado após o usuário provar que registrou o segredo."""
    _, csrf = usuario_com_token

    cliente.post("/usuarios/me/mfa/iniciar", headers=cabecalho(csrf))

    resposta = cliente.post(
        "/usuarios/me/mfa/confirmar",
        json={"codigo": "000000"},
        headers=cabecalho(csrf),
    )
    assert resposta.status_code == 400

    assert cliente.get("/usuarios/me/mfa").json()["ativado"] is False


def test_login_com_mfa_nao_abre_sessao_direto(cliente, usuario_com_token):
    """Com MFA ativo, a senha sozinha não dá acesso aos dados."""
    _, csrf = usuario_com_token
    _ativar_mfa(cliente, csrf)

    navegador = TestClient(cliente.app)
    resposta = navegador.post(
        "/auth/login", data={"username": "alice", "password": SENHA_VALIDA}
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["mfa_requerido"] is True
    assert corpo["token_de_desafio"]

    # Nenhuma sessão foi aberta.
    assert navegador.get("/usuarios/me").status_code == 401


def test_token_de_desafio_nao_da_acesso_aos_dados(cliente, usuario_com_token):
    """O token de desafio não é aceito nos endpoints de dados.

    Sem essa checagem, o primeiro fator sozinho bastaria — o que anularia o
    segundo fator por completo.
    """
    _, csrf = usuario_com_token
    _ativar_mfa(cliente, csrf)

    navegador = TestClient(cliente.app)
    desafio = navegador.post(
        "/auth/login", data={"username": "alice", "password": SENHA_VALIDA}
    ).json()["token_de_desafio"]

    resposta = navegador.get(
        "/usuarios/me", headers={"Authorization": f"Bearer {desafio}"}
    )
    assert resposta.status_code == 401


def test_login_completo_com_codigo_totp(cliente, usuario_com_token):
    """Um código TOTP válido conclui o login e abre a sessão."""
    _, csrf = usuario_com_token
    segredo, _ = _ativar_mfa(cliente, csrf)

    navegador = TestClient(cliente.app)
    desafio = navegador.post(
        "/auth/login", data={"username": "alice", "password": SENHA_VALIDA}
    ).json()["token_de_desafio"]

    resposta = navegador.post(
        "/auth/mfa/verificar",
        json={"token_de_desafio": desafio, "codigo": mfa.gerar_codigo(segredo)},
    )
    assert resposta.status_code == 200
    assert navegador.get("/usuarios/me").status_code == 200


def test_codigo_totp_invalido_e_recusado(cliente, usuario_com_token):
    """Um código errado não conclui o login."""
    _, csrf = usuario_com_token
    _ativar_mfa(cliente, csrf)

    navegador = TestClient(cliente.app)
    desafio = navegador.post(
        "/auth/login", data={"username": "alice", "password": SENHA_VALIDA}
    ).json()["token_de_desafio"]

    resposta = navegador.post(
        "/auth/mfa/verificar",
        json={"token_de_desafio": desafio, "codigo": "000000"},
    )
    assert resposta.status_code == 401


def test_codigo_de_recuperacao_funciona_uma_unica_vez(cliente, usuario_com_token):
    """Um código de recuperação autentica e depois deixa de valer."""
    _, csrf = usuario_com_token
    _, codigos = _ativar_mfa(cliente, csrf)
    codigo = codigos[0]

    def _tentar(codigo_usado: str):
        """Executa um login completo usando o código informado.

        Args:
            codigo_usado (str): O código de recuperação a apresentar.

        Returns:
            Response: A resposta da verificação do segundo fator.
        """
        navegador = TestClient(cliente.app)
        desafio = navegador.post(
            "/auth/login", data={"username": "alice", "password": SENHA_VALIDA}
        ).json()["token_de_desafio"]
        return navegador.post(
            "/auth/mfa/verificar",
            json={"token_de_desafio": desafio, "codigo": codigo_usado},
        )

    assert _tentar(codigo).status_code == 200
    assert _tentar(codigo).status_code == 401


def test_desativar_mfa_exige_senha(cliente, usuario_com_token):
    """Remover o segundo fator sem a senha correta é recusado.

    Impede que quem sequestrou uma sessão — mas não sabe a senha — desligue a
    proteção que o impediria de voltar.
    """
    _, csrf = usuario_com_token
    _ativar_mfa(cliente, csrf)

    resposta = cliente.post(
        "/usuarios/me/mfa/desativar",
        json={"senha": "SenhaErrada#2026"},
        headers=cabecalho(csrf),
    )
    assert resposta.status_code == 400
    assert cliente.get("/usuarios/me/mfa").json()["ativado"] is True

    resposta = cliente.post(
        "/usuarios/me/mfa/desativar",
        json={"senha": SENHA_VALIDA},
        headers=cabecalho(csrf),
    )
    assert resposta.status_code == 200
    assert cliente.get("/usuarios/me/mfa").json()["ativado"] is False


# --- Criptografia em repouso ---


def test_pii_fica_cifrada_no_banco(cliente, usuario_com_token):
    """Nome, e-mail e observações não aparecem em claro na tabela."""
    _, csrf = usuario_com_token

    cliente.put(
        "/usuarios/me",
        json={"nome_completo": "Alice Silva", "email": "alice@exemplo.com"},
        headers=cabecalho(csrf),
    )

    resposta_categoria = cliente.post(
        "/categorias/",
        json={"nome": "Consultas Médicas", "tipo": "Gasto", "cor": "#1ABC9C"},
        headers=cabecalho(csrf),
    )
    assert resposta_categoria.status_code == 201, resposta_categoria.text
    categoria = resposta_categoria.json()

    cliente.post(
        "/transacoes/",
        json={
            "descricao": "Consulta",
            "valor": "300.00",
            "categoria_id": categoria["id"],
            "data": "2026-03-01T10:00:00Z",
            "observacoes": "anotação clínica confidencial",
        },
        params=PERIODO,
        headers=cabecalho(csrf),
    )

    from sqlalchemy import text

    db = SessionLocal()
    try:
        bruto_usuario = db.execute(
            text("SELECT nome_completo, email, email_indice FROM usuarios")
        ).first()
        bruto_transacao = db.execute(
            text("SELECT observacoes FROM transacoes")
        ).first()
    finally:
        db.close()

    assert "Alice Silva" not in str(bruto_usuario)
    assert "alice@exemplo.com" not in str(bruto_usuario)
    assert "anotação clínica confidencial" not in str(bruto_transacao)

    # E o índice cego também não revela o endereço.
    assert "alice" not in bruto_usuario[2]


def test_pii_volta_legivel_pela_api(cliente, usuario_com_token):
    """A cifragem é transparente: a API continua devolvendo os valores."""
    _, csrf = usuario_com_token

    cliente.put(
        "/usuarios/me",
        json={"nome_completo": "Alice Silva", "email": "alice@exemplo.com"},
        headers=cabecalho(csrf),
    )

    perfil = cliente.get("/usuarios/me").json()
    assert perfil["nome_completo"] == "Alice Silva"
    assert perfil["email"] == "alice@exemplo.com"


def test_busca_por_email_usa_indice_cego(cliente, usuario_com_token):
    """O e-mail continua pesquisável apesar de cifrado."""
    _, csrf = usuario_com_token

    cliente.put(
        "/usuarios/me",
        json={"email": "Alice@Exemplo.COM"},
        headers=cabecalho(csrf),
    )

    db = SessionLocal()
    try:
        # A busca normaliza maiúsculas/minúsculas antes do HMAC.
        encontrado = crud.get_usuario_por_email(db, "alice@exemplo.com")
        assert encontrado is not None
        assert encontrado.nome_usuario == "alice"
    finally:
        db.close()


# --- CORS ---


def test_preflight_aceita_os_cabecalhos_que_o_frontend_envia(cliente):
    """O preflight precisa liberar todo cabeçalho usado pelo cliente.

    Um cabeçalho ausente da allowlist faz o navegador reprovar o preflight, e
    a requisição sequer chega à aplicação — falha invisível para os testes que
    chamam a API diretamente, porque o `TestClient` não simula CORS.
    """
    resposta = cliente.options(
        "/transacoes/",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token,idempotency-key",
        },
    )

    assert resposta.status_code == 200, resposta.text

    liberados = {
        h.strip().lower()
        for h in resposta.headers["access-control-allow-headers"].split(",")
    }
    assert {"x-csrf-token", "idempotency-key", "content-type"} <= liberados
