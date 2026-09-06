# Arquivo: tests/test_integridade_financeira.py
"""Testes de Integridade Contábil e Transacional.

Cobrem o bug em que categorias com tipo fora de 'Gasto'/'Receita' sumiam
silenciosamente dos totais, além de precisão monetária, idempotência e
preservação do histórico.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from conftest import cabecalho

PERIODO = {"data_inicio": "2026-03-01", "data_fim": "2026-03-31"}


def _categoria(cliente, token, nome, tipo="Gasto"):
    """Cria uma categoria e devolve seu corpo.

    Args:
        cliente: Cliente HTTP de teste.
        token (str): Token de acesso.
        nome (str): Nome da categoria.
        tipo (str): 'Gasto' ou 'Receita'.

    Returns:
        dict: A categoria criada.
    """
    resposta = cliente.post(
        "/categorias/",
        json={"nome": nome, "tipo": tipo, "cor": "#FF0000"},
        headers=cabecalho(token),
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _lancar(cliente, token, categoria_id, valor, descricao="Lançamento", headers=None):
    """Registra uma transação e devolve a resposta HTTP.

    Args:
        cliente: Cliente HTTP de teste.
        token (str): Token de acesso.
        categoria_id (int): Categoria do lançamento.
        valor (str): Valor monetário.
        descricao (str): Descrição do lançamento.
        headers (dict | None): Cabeçalhos que substituem o padrão, quando dado.

    Returns:
        Response: A resposta HTTP.
    """
    return cliente.post(
        "/transacoes/",
        json={
            "descricao": descricao,
            "valor": valor,
            "categoria_id": categoria_id,
            "data": "2026-03-15T12:00:00Z",
        },
        params=PERIODO,
        headers=headers if headers is not None else cabecalho(token),
    )


@pytest.mark.parametrize("tipo_invalido", ["Despesa", "gasto", "RECEITA", "Outro", ""])
def test_tipo_de_categoria_fora_do_dominio_e_rejeitado(
    cliente, usuario_com_token, tipo_invalido
):
    """A API recusa tipos que o dashboard não sabe somar.

    Antes, um valor como 'Despesa' era aceito e o dinheiro daquela categoria
    simplesmente não aparecia em nenhum total.

    Args:
        tipo_invalido (str): O tipo fora do domínio sob teste.
    """
    _, token = usuario_com_token

    resposta = cliente.post(
        "/categorias/",
        json={"nome": "Teste", "tipo": tipo_invalido, "cor": "#FF0000"},
        headers=cabecalho(token),
    )
    assert resposta.status_code == 422


def test_dashboard_soma_todas_as_categorias_criadas(cliente, usuario_com_token):
    """Todo valor lançado aparece nos totais do dashboard."""
    _, token = usuario_com_token

    gasto = _categoria(cliente, token, "Aluguel", "Gasto")
    receita = _categoria(cliente, token, "Salário Extra", "Receita")

    _lancar(cliente, token, gasto["id"], "1200.00")
    _lancar(cliente, token, receita["id"], "5000.00")

    dashboard = cliente.get(
        "/dashboard/", params=PERIODO, headers=cabecalho(token)
    ).json()

    assert Decimal(dashboard["total_gastos"]) == Decimal("1200.00")
    assert Decimal(dashboard["total_receitas"]) == Decimal("5000.00")
    assert Decimal(dashboard["lucro_liquido"]) == Decimal("3800.00")


@pytest.mark.parametrize("valor", ["0", "-10.00", "-0.01"])
def test_valor_nao_positivo_e_rejeitado(cliente, usuario_com_token, valor):
    """Valores zero ou negativos são recusados.

    O sinal do lançamento vem do tipo da categoria; um valor negativo inverteria
    o resultado do dashboard sem qualquer sinalização.

    Args:
        valor (str): O valor inválido sob teste.
    """
    _, token = usuario_com_token
    categoria = _categoria(cliente, token, "Compras")

    assert _lancar(cliente, token, categoria["id"], valor).status_code == 422


def test_valor_acima_do_teto_e_rejeitado(cliente, usuario_com_token):
    """Um valor maior que a coluna suporta gera 422, não erro interno."""
    _, token = usuario_com_token
    categoria = _categoria(cliente, token, "Compras")

    assert _lancar(
        cliente, token, categoria["id"], "99999999999999999.00"
    ).status_code == 422


def test_precisao_monetaria_e_exata(cliente, usuario_com_token):
    """Somas de centavos não sofrem erro de ponto flutuante."""
    _, token = usuario_com_token
    categoria = _categoria(cliente, token, "Miudezas")

    for _ in range(3):
        _lancar(cliente, token, categoria["id"], "0.10")

    dashboard = cliente.get(
        "/dashboard/", params=PERIODO, headers=cabecalho(token)
    ).json()

    # Em ponto flutuante, 0.1 * 3 == 0.30000000000000004.
    assert Decimal(dashboard["total_gastos"]) == Decimal("0.30")


def test_chave_de_idempotencia_evita_duplicacao(cliente, usuario_com_token):
    """Reenviar a mesma chave não cria um segundo lançamento.

    Cobre o retry automático do cliente e a fila de sincronização offline.
    """
    _, token = usuario_com_token
    categoria = _categoria(cliente, token, "Compras")

    chave = {"Idempotency-Key": "b7f3c2a1-0000-4000-8000-000000000001"}
    cabecalhos = {**cabecalho(token), **chave}

    for _ in range(3):
        resposta = _lancar(
            cliente,
            token,
            categoria["id"],
            "250.00",
            headers=cabecalhos,
        )
        assert resposta.status_code == 201

    transacoes = cliente.get("/transacoes/", headers=cabecalho(token)).json()
    assert len(transacoes) == 1

    dashboard = cliente.get(
        "/dashboard/", params=PERIODO, headers=cabecalho(token)
    ).json()
    assert Decimal(dashboard["total_gastos"]) == Decimal("250.00")


def test_sem_chave_de_idempotencia_lancamentos_repetem(cliente, usuario_com_token):
    """Sem a chave, dois lançamentos idênticos são registros distintos.

    Isso é intencional: pagar duas vezes o mesmo valor no mesmo dia é legítimo.
    """
    _, token = usuario_com_token
    categoria = _categoria(cliente, token, "Café")

    _lancar(cliente, token, categoria["id"], "5.00")
    _lancar(cliente, token, categoria["id"], "5.00")

    assert len(cliente.get("/transacoes/", headers=cabecalho(token)).json()) == 2


def test_categoria_em_uso_nao_pode_ser_removida(cliente, usuario_com_token):
    """Apagar categoria com lançamentos é bloqueado, preservando o histórico."""
    _, token = usuario_com_token
    categoria = _categoria(cliente, token, "Histórico")
    _lancar(cliente, token, categoria["id"], "42.00")

    resposta = cliente.delete(
        f"/categorias/{categoria['id']}", headers=cabecalho(token)
    )
    assert resposta.status_code == 400

    # A transação continua íntegra e classificada.
    transacoes = cliente.get("/transacoes/", headers=cabecalho(token)).json()
    assert transacoes[0]["categoria"]["nome"] == "Histórico"


def test_categoria_sem_uso_pode_ser_removida(cliente, usuario_com_token):
    """Sem lançamentos vinculados, a remoção é permitida."""
    _, token = usuario_com_token
    categoria = _categoria(cliente, token, "Descartável")

    resposta = cliente.delete(
        f"/categorias/{categoria['id']}", headers=cabecalho(token)
    )
    assert resposta.status_code == 200


def test_data_futura_e_rejeitada(cliente, usuario_com_token):
    """Lançamentos com data muito à frente não são aceitos."""
    _, token = usuario_com_token
    categoria = _categoria(cliente, token, "Compras")

    resposta = cliente.post(
        "/transacoes/",
        json={
            "descricao": "Do futuro",
            "valor": "10.00",
            "categoria_id": categoria["id"],
            "data": "2099-01-01T00:00:00Z",
        },
        params={"data_inicio": "2099-01-01", "data_fim": "2099-01-31"},
        headers=cabecalho(token),
    )
    assert resposta.status_code == 422


def test_periodo_invertido_e_rejeitado(cliente, usuario_com_token):
    """Data inicial posterior à final produz 422."""
    _, token = usuario_com_token

    resposta = cliente.get(
        "/dashboard/",
        params={"data_inicio": "2026-12-31", "data_fim": "2026-01-01"},
        headers=cabecalho(token),
    )
    assert resposta.status_code == 422


def test_periodo_excessivamente_longo_e_rejeitado(cliente, usuario_com_token):
    """Intervalos absurdos são recusados antes de varrer o banco."""
    _, token = usuario_com_token

    resposta = cliente.get(
        "/dashboard/",
        params={"data_inicio": "1900-01-01", "data_fim": "2026-12-31"},
        headers=cabecalho(token),
    )
    assert resposta.status_code == 422


def test_paginacao_tem_teto(cliente, usuario_com_token):
    """O parâmetro `limit` não aceita valores acima do teto."""
    _, token = usuario_com_token

    resposta = cliente.get(
        "/transacoes/", params={"limit": 100000}, headers=cabecalho(token)
    )
    assert resposta.status_code == 422


def test_edicao_registra_valores_anterior_e_novo(cliente, usuario_com_token):
    """A edição de uma transação altera o dashboard de forma consistente."""
    _, token = usuario_com_token
    categoria = _categoria(cliente, token, "Compras")
    _lancar(cliente, token, categoria["id"], "100.00")

    transacao = cliente.get("/transacoes/", headers=cabecalho(token)).json()[0]

    resposta = cliente.put(
        f"/transacoes/{transacao['id']}",
        json={
            "descricao": "Corrigido",
            "valor": "175.50",
            "categoria_id": categoria["id"],
            "data": "2026-03-15T12:00:00Z",
        },
        params=PERIODO,
        headers=cabecalho(token),
    )
    assert resposta.status_code == 200
    assert Decimal(resposta.json()["total_gastos"]) == Decimal("175.50")
