# Arquivo: tests/test_isolamento_entre_usuarios.py
"""Testes de Isolamento Multiusuário (IDOR).

Cobrem a falha mais grave encontrada na auditoria: categorias eram globais, o
que permitia a qualquer usuário autenticado listar, renomear e apagar as
categorias de todos os outros — e, por consequência, corromper a classificação
contábil alheia.
"""

from __future__ import annotations

from conftest import autenticar, cabecalho, criar_conta


def _criar_categoria(cliente, token, nome, tipo="Gasto", cor="#FF0000"):
    """Cria uma categoria para o usuário autenticado.

    Args:
        cliente: Cliente HTTP de teste.
        token (str): Token de acesso.
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


def test_usuario_nao_ve_categorias_de_outro(cliente, dois_usuarios):
    """A listagem de categorias devolve apenas as do próprio usuário."""
    token_alice, token_bob = dois_usuarios

    _criar_categoria(cliente, token_alice, "Segredo da Alice")

    categorias_bob = cliente.get(
        "/categorias/", headers=cabecalho(token_bob)
    ).json()

    nomes = {c["nome"] for c in categorias_bob}
    assert "Segredo da Alice" not in nomes


def test_usuario_nao_edita_categoria_de_outro(cliente, dois_usuarios):
    """Editar a categoria de outro usuário retorna 404, não sucesso."""
    token_alice, token_bob = dois_usuarios

    categoria = _criar_categoria(cliente, token_alice, "Da Alice")

    resposta = cliente.put(
        f"/categorias/{categoria['id']}",
        json={"nome": "Sequestrada"},
        headers=cabecalho(token_bob),
    )
    assert resposta.status_code == 404

    # E a categoria original permanece intacta.
    categorias_alice = cliente.get(
        "/categorias/", headers=cabecalho(token_alice)
    ).json()
    assert any(c["nome"] == "Da Alice" for c in categorias_alice)


def test_usuario_nao_deleta_categoria_de_outro(cliente, dois_usuarios):
    """Apagar a categoria de outro usuário retorna 404 e não remove nada."""
    token_alice, token_bob = dois_usuarios

    categoria = _criar_categoria(cliente, token_alice, "Preservar")

    resposta = cliente.delete(
        f"/categorias/{categoria['id']}", headers=cabecalho(token_bob)
    )
    assert resposta.status_code == 404

    categorias_alice = cliente.get(
        "/categorias/", headers=cabecalho(token_alice)
    ).json()
    assert any(c["nome"] == "Preservar" for c in categorias_alice)


def test_transacao_nao_pode_referenciar_categoria_de_outro(cliente, dois_usuarios):
    """Criar transação apontando para categoria alheia é rejeitado."""
    token_alice, token_bob = dois_usuarios

    categoria_alice = _criar_categoria(cliente, token_alice, "Exclusiva")

    resposta = cliente.post(
        "/transacoes/",
        json={
            "descricao": "Tentativa de vínculo cruzado",
            "valor": "10.00",
            "categoria_id": categoria_alice["id"],
            "data": "2026-03-01T10:00:00Z",
        },
        params={"data_inicio": "2026-03-01", "data_fim": "2026-03-31"},
        headers=cabecalho(token_bob),
    )
    assert resposta.status_code == 404


def test_usuario_nao_ve_transacoes_de_outro(cliente, dois_usuarios):
    """O extrato devolve apenas as transações do próprio usuário."""
    token_alice, token_bob = dois_usuarios

    categoria = _criar_categoria(cliente, token_alice, "Compras")
    cliente.post(
        "/transacoes/",
        json={
            "descricao": "Compra privada da Alice",
            "valor": "999.99",
            "categoria_id": categoria["id"],
            "data": "2026-03-01T10:00:00Z",
        },
        params={"data_inicio": "2026-03-01", "data_fim": "2026-03-31"},
        headers=cabecalho(token_alice),
    )

    transacoes_bob = cliente.get(
        "/transacoes/", headers=cabecalho(token_bob)
    ).json()
    assert transacoes_bob == []

    dashboard_bob = cliente.get(
        "/dashboard/",
        params={"data_inicio": "2026-03-01", "data_fim": "2026-03-31"},
        headers=cabecalho(token_bob),
    ).json()
    assert dashboard_bob["total_gastos"] == "0"


def test_usuario_nao_edita_transacao_de_outro(cliente, dois_usuarios):
    """Editar transação alheia retorna 404 e não altera o valor."""
    token_alice, token_bob = dois_usuarios

    categoria_alice = _criar_categoria(cliente, token_alice, "Compras")
    cliente.post(
        "/transacoes/",
        json={
            "descricao": "Original",
            "valor": "100.00",
            "categoria_id": categoria_alice["id"],
            "data": "2026-03-01T10:00:00Z",
        },
        params={"data_inicio": "2026-03-01", "data_fim": "2026-03-31"},
        headers=cabecalho(token_alice),
    )
    transacao = cliente.get(
        "/transacoes/", headers=cabecalho(token_alice)
    ).json()[0]

    categoria_bob = _criar_categoria(cliente, token_bob, "Do Bob")
    resposta = cliente.put(
        f"/transacoes/{transacao['id']}",
        json={
            "descricao": "Alterada pelo Bob",
            "valor": "1.00",
            "categoria_id": categoria_bob["id"],
            "data": "2026-03-01T10:00:00Z",
        },
        params={"data_inicio": "2026-03-01", "data_fim": "2026-03-31"},
        headers=cabecalho(token_bob),
    )
    assert resposta.status_code == 404

    inalterada = cliente.get(
        "/transacoes/", headers=cabecalho(token_alice)
    ).json()[0]
    assert inalterada["descricao"] == "Original"
    assert inalterada["valor"] == "100.00"


def test_usuario_nao_deleta_transacao_de_outro(cliente, dois_usuarios):
    """Apagar transação alheia retorna 404 e o registro permanece."""
    token_alice, token_bob = dois_usuarios

    categoria = _criar_categoria(cliente, token_alice, "Compras")
    cliente.post(
        "/transacoes/",
        json={
            "descricao": "Não apagar",
            "valor": "50.00",
            "categoria_id": categoria["id"],
            "data": "2026-03-01T10:00:00Z",
        },
        params={"data_inicio": "2026-03-01", "data_fim": "2026-03-31"},
        headers=cabecalho(token_alice),
    )
    transacao = cliente.get(
        "/transacoes/", headers=cabecalho(token_alice)
    ).json()[0]

    resposta = cliente.delete(
        f"/transacoes/{transacao['id']}",
        params={"data_inicio": "2026-03-01", "data_fim": "2026-03-31"},
        headers=cabecalho(token_bob),
    )
    assert resposta.status_code == 404

    assert len(cliente.get("/transacoes/", headers=cabecalho(token_alice)).json()) == 1


def test_nomes_de_categoria_podem_repetir_entre_usuarios(cliente, dois_usuarios):
    """Dois usuários podem ter categorias com o mesmo nome.

    Antes, o nome era único globalmente: a colisão revelava a existência de uma
    categoria de outro usuário e impedia o cadastro.
    """
    token_alice, token_bob = dois_usuarios

    _criar_categoria(cliente, token_alice, "Viagem")
    _criar_categoria(cliente, token_bob, "Viagem")


def test_novo_usuario_recebe_categorias_padrao(cliente):
    """Uma conta recém-criada já vem com categorias próprias utilizáveis."""
    criar_conta(cliente, "novato")
    token = autenticar(cliente, "novato")

    categorias = cliente.get("/categorias/", headers=cabecalho(token)).json()

    assert len(categorias) > 0
    assert {c["tipo"] for c in categorias} == {"Gasto", "Receita"}
