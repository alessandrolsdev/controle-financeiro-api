# Arquivo: tests/test_isolamento_entre_usuarios.py
"""Testes de Isolamento Multiusuário (IDOR).

Cobrem a falha mais grave encontrada na auditoria: categorias eram globais, o
que permitia a qualquer usuário autenticado listar, renomear e apagar as
categorias de todos os outros — e, por consequência, corromper a classificação
contábil alheia.

Com autenticação por cookie, cada usuário precisa do seu próprio `TestClient`:
os dois compartilhariam o jar de cookies e o segundo login sobrescreveria a
sessão do primeiro. A fixture `dois_clientes` representa dois navegadores.
"""

from __future__ import annotations

from conftest import autenticar, cabecalho, criar_conta

PERIODO = {"data_inicio": "2026-03-01", "data_fim": "2026-03-31"}


def _criar_categoria(cliente, token, nome, tipo="Gasto", cor="#FF0000"):
    """Cria uma categoria para o usuário autenticado no cliente informado.

    Args:
        cliente: Cliente HTTP daquele usuário.
        token (str): Token CSRF da sessão.
        nome (str): Nome da categoria.
        tipo (str): 'Gasto' ou 'Receita'.
        cor (str): Cor hexadecimal.

    Returns:
        dict: A categoria criada.
    """
    resposta = cliente.post(
        "/categorias/",
        json={"nome": nome, "tipo": tipo, "cor": cor},
        headers=cabecalho(token),
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _lancar(cliente, token, categoria_id, valor, descricao):
    """Registra uma transação para o usuário do cliente informado.

    Args:
        cliente: Cliente HTTP daquele usuário.
        token (str): Token CSRF da sessão.
        categoria_id (int): Categoria do lançamento.
        valor (str): Valor monetário.
        descricao (str): Descrição do lançamento.

    Returns:
        Response: A resposta HTTP.
    """
    return cliente.post(
        "/transacoes/",
        json={
            "descricao": descricao,
            "valor": valor,
            "categoria_id": categoria_id,
            "data": "2026-03-01T10:00:00Z",
        },
        params=PERIODO,
        headers=cabecalho(token),
    )


def test_usuario_nao_ve_categorias_de_outro(dois_clientes):
    """A listagem de categorias devolve apenas as do próprio usuário."""
    (alice, csrf_alice), (bob, csrf_bob) = dois_clientes

    _criar_categoria(alice, csrf_alice, "Segredo da Alice")

    categorias_bob = bob.get("/categorias/").json()

    assert "Segredo da Alice" not in {c["nome"] for c in categorias_bob}


def test_usuario_nao_edita_categoria_de_outro(dois_clientes):
    """Editar a categoria de outro usuário retorna 404, não sucesso."""
    (alice, csrf_alice), (bob, csrf_bob) = dois_clientes

    categoria = _criar_categoria(alice, csrf_alice, "Da Alice")

    resposta = bob.put(
        f"/categorias/{categoria['id']}",
        json={"nome": "Sequestrada"},
        headers=cabecalho(csrf_bob),
    )
    assert resposta.status_code == 404

    # E a categoria original permanece intacta.
    assert any(c["nome"] == "Da Alice" for c in alice.get("/categorias/").json())


def test_usuario_nao_deleta_categoria_de_outro(dois_clientes):
    """Apagar a categoria de outro usuário retorna 404 e não remove nada."""
    (alice, csrf_alice), (bob, csrf_bob) = dois_clientes

    categoria = _criar_categoria(alice, csrf_alice, "Preservar")

    resposta = bob.delete(
        f"/categorias/{categoria['id']}", headers=cabecalho(csrf_bob)
    )
    assert resposta.status_code == 404

    assert any(c["nome"] == "Preservar" for c in alice.get("/categorias/").json())


def test_transacao_nao_pode_referenciar_categoria_de_outro(dois_clientes):
    """Criar transação apontando para categoria alheia é rejeitado."""
    (alice, csrf_alice), (bob, csrf_bob) = dois_clientes

    categoria_alice = _criar_categoria(alice, csrf_alice, "Exclusiva")

    resposta = _lancar(
        bob, csrf_bob, categoria_alice["id"], "10.00", "Vínculo cruzado"
    )
    assert resposta.status_code == 404


def test_usuario_nao_ve_transacoes_de_outro(dois_clientes):
    """O extrato devolve apenas as transações do próprio usuário."""
    (alice, csrf_alice), (bob, csrf_bob) = dois_clientes

    categoria = _criar_categoria(alice, csrf_alice, "Compras")
    _lancar(alice, csrf_alice, categoria["id"], "999.99", "Compra da Alice")

    assert bob.get("/transacoes/").json() == []

    dashboard_bob = bob.get("/dashboard/", params=PERIODO).json()
    assert dashboard_bob["total_gastos"] == "0"


def test_usuario_nao_edita_transacao_de_outro(dois_clientes):
    """Editar transação alheia retorna 404 e não altera o valor."""
    (alice, csrf_alice), (bob, csrf_bob) = dois_clientes

    categoria_alice = _criar_categoria(alice, csrf_alice, "Compras")
    _lancar(alice, csrf_alice, categoria_alice["id"], "100.00", "Original")
    transacao = alice.get("/transacoes/").json()[0]

    categoria_bob = _criar_categoria(bob, csrf_bob, "Do Bob")
    resposta = bob.put(
        f"/transacoes/{transacao['id']}",
        json={
            "descricao": "Alterada pelo Bob",
            "valor": "1.00",
            "categoria_id": categoria_bob["id"],
            "data": "2026-03-01T10:00:00Z",
        },
        params=PERIODO,
        headers=cabecalho(csrf_bob),
    )
    assert resposta.status_code == 404

    inalterada = alice.get("/transacoes/").json()[0]
    assert inalterada["descricao"] == "Original"
    assert inalterada["valor"] == "100.00"


def test_usuario_nao_deleta_transacao_de_outro(dois_clientes):
    """Apagar transação alheia retorna 404 e o registro permanece."""
    (alice, csrf_alice), (bob, csrf_bob) = dois_clientes

    categoria = _criar_categoria(alice, csrf_alice, "Compras")
    _lancar(alice, csrf_alice, categoria["id"], "50.00", "Não apagar")
    transacao = alice.get("/transacoes/").json()[0]

    resposta = bob.delete(
        f"/transacoes/{transacao['id']}",
        params=PERIODO,
        headers=cabecalho(csrf_bob),
    )
    assert resposta.status_code == 404

    assert len(alice.get("/transacoes/").json()) == 1


def test_nomes_de_categoria_podem_repetir_entre_usuarios(dois_clientes):
    """Dois usuários podem ter categorias com o mesmo nome.

    Antes, o nome era único globalmente: a colisão revelava a existência de uma
    categoria de outro usuário e impedia o cadastro.
    """
    (alice, csrf_alice), (bob, csrf_bob) = dois_clientes

    _criar_categoria(alice, csrf_alice, "Viagem")
    _criar_categoria(bob, csrf_bob, "Viagem")


def test_emails_iguais_sao_rejeitados_entre_usuarios(dois_clientes):
    """A unicidade de e-mail sobrevive à criptografia.

    O e-mail é cifrado com nonce aleatório, então a coluna não é comparável.
    A unicidade passa a ser garantida pelo índice cego — este teste verifica
    que ela continua valendo.
    """
    (alice, csrf_alice), (bob, csrf_bob) = dois_clientes

    resposta = alice.put(
        "/usuarios/me",
        json={"email": "mesmo@exemplo.com"},
        headers=cabecalho(csrf_alice),
    )
    assert resposta.status_code == 200

    resposta = bob.put(
        "/usuarios/me",
        json={"email": "mesmo@exemplo.com"},
        headers=cabecalho(csrf_bob),
    )
    assert resposta.status_code == 400


def test_novo_usuario_recebe_categorias_padrao(cliente):
    """Uma conta recém-criada já vem com categorias próprias utilizáveis."""
    criar_conta(cliente, "novato")
    autenticar(cliente, "novato")

    categorias = cliente.get("/categorias/").json()

    assert len(categorias) > 0
    assert {c["tipo"] for c in categorias} == {"Gasto", "Receita"}
