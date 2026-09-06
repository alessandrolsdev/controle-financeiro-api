# Arquivo: tests/test_importacao.py
"""Testes da Importação de Planilhas (issue #2)."""

from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal

import pytest
from conftest import cabecalho

from backend import importacao

PERIODO = {"data_inicio": "2026-01-01", "data_fim": "2026-12-31"}


# --- Conversão de valores ---


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("1.234,56", Decimal("1234.56")),      # formato brasileiro
        ("1,234.56", Decimal("1234.56")),      # formato anglófono
        ("R$ 1.234,56", Decimal("1234.56")),   # com símbolo de moeda
        ("-150,00", Decimal("150.00")),        # negativo vira absoluto
        ("(150,00)", Decimal("150.00")),       # parênteses contábeis
        ("1234.56", Decimal("1234.56")),
        ("99", Decimal("99.00")),
        (1234.56, Decimal("1234.56")),         # já numérico
    ],
)
def test_conversao_de_valor(entrada, esperado):
    """Valores em formatos usuais de extrato são interpretados corretamente.

    Args:
        entrada: O valor como aparece na planilha.
        esperado (Decimal): O valor esperado após a conversão.
    """
    assert importacao.converter_valor(entrada) == esperado


@pytest.mark.parametrize("entrada", ["", "abc", None, "R$"])
def test_valor_invalido_e_rejeitado(entrada):
    """Valores não numéricos produzem erro, não um silencioso zero.

    Args:
        entrada: O valor inválido sob teste.
    """
    with pytest.raises(ValueError):
        importacao.converter_valor(entrada)


@pytest.mark.parametrize(
    "entrada,ano,mes,dia",
    [
        ("03/04/2026", 2026, 4, 3),      # brasileiro: 3 de abril
        ("2026-04-03", 2026, 4, 3),      # ISO
        ("03-04-2026", 2026, 4, 3),
        ("03/04/2026 14:30", 2026, 4, 3),
    ],
)
def test_conversao_de_data(entrada, ano, mes, dia):
    """Datas em formatos usuais são lidas, com o padrão brasileiro primeiro.

    Args:
        entrada (str): A data como aparece na planilha.
        ano (int): Ano esperado.
        mes (int): Mês esperado.
        dia (int): Dia esperado.
    """
    resultado = importacao.converter_data(entrada)
    assert (resultado.year, resultado.month, resultado.day) == (ano, mes, dia)


def test_data_invalida_e_rejeitada():
    """Uma data ininteligível produz erro."""
    with pytest.raises(ValueError):
        importacao.converter_data("ontem")


# --- Categorização automática ---


@pytest.mark.parametrize(
    "descricao,esperado",
    [
        ("POSTO IPIRANGA CENTRO", "Transporte"),
        ("UBER *TRIP", "Transporte"),
        ("ATACADAO SP", "Alimentação"),
        ("IFOOD *RESTAURANTE", "Alimentação"),
        ("DROGARIA SAO PAULO", "Saúde"),
        ("NETFLIX.COM", "Lazer"),
        ("ALUGUEL APTO 42", "Moradia"),
    ],
)
def test_categoria_e_adivinhada_pela_descricao(descricao, esperado):
    """A heurística de palavras-chave classifica descrições típicas.

    Args:
        descricao (str): A descrição do lançamento.
        esperado (str): A categoria esperada.
    """
    assert importacao.adivinhar_categoria(descricao, "Gasto") == esperado


def test_descricao_desconhecida_nao_e_categorizada():
    """Sem palavra-chave conhecida, nenhuma categoria é inventada."""
    assert importacao.adivinhar_categoria("XPTO 12345", "Gasto") is None


# --- Segurança ---


def test_formulas_sao_neutralizadas():
    """Texto que o Excel executaria como fórmula é neutralizado.

    Sem isso, exportar os dados de volta para CSV reintroduz a fórmula, que o
    Excel executa ao abrir o arquivo.
    """
    perigoso = "=cmd|'/c calc'!A1"
    assert importacao.neutralizar_formula(perigoso).startswith("'")

    for prefixo in ("+", "-", "@"):
        assert importacao.neutralizar_formula(f"{prefixo}SUM(A1)").startswith("'")


def test_arquivo_grande_demais_e_rejeitado():
    """Um arquivo acima do limite é recusado antes do processamento."""
    conteudo = b"x" * (importacao.TAMANHO_MAXIMO_ARQUIVO + 1)

    with pytest.raises(importacao.ArquivoInvalidoError, match="limite"):
        importacao.ler_planilha("grande.csv", conteudo)


def test_extensao_nao_suportada_e_rejeitada():
    """Formatos fora da allowlist são recusados."""
    with pytest.raises(importacao.ArquivoInvalidoError, match="não suportado"):
        importacao.ler_planilha("script.exe", b"conteudo")


def test_planilha_sem_colunas_obrigatorias_e_rejeitada():
    """Falta de coluna essencial produz mensagem explicativa."""
    csv = b"coluna_a;coluna_b\n1;2\n"

    with pytest.raises(importacao.ArquivoInvalidoError, match="precisa ter as colunas"):
        importacao.ler_planilha("ruim.csv", csv)


# --- Leitura de CSV ---


def test_leitura_de_csv_brasileiro():
    """Um CSV com ponto e vírgula, acentos e valores em pt-BR é lido."""
    csv = (
        "Data;Descrição;Valor;Categoria\n"
        "03/04/2026;POSTO IPIRANGA;-150,50;\n"
        "04/04/2026;Salário;5.000,00;Salário\n"
    ).encode()

    resultado = importacao.ler_planilha("extrato.csv", csv)

    assert len(resultado.linhas) == 2
    assert resultado.erros == []

    primeira = resultado.linhas[0]
    assert primeira.valor == Decimal("150.50")
    assert primeira.tipo == "Gasto"
    assert primeira.categoria_sugerida == "Transporte"

    assert resultado.linhas[1].categoria_sugerida == "Salário"


def test_linhas_invalidas_nao_derrubam_o_arquivo():
    """Uma linha ruim é reportada; as demais são importadas."""
    csv = (
        b"Data,Descricao,Valor\n"
        b"03/04/2026,Boa,100.00\n"
        b"data-invalida,Ruim,100.00\n"
        b"05/04/2026,Sem valor,\n"
        b"06/04/2026,Outra boa,50.00\n"
    )

    resultado = importacao.ler_planilha("misto.csv", csv)

    assert len(resultado.linhas) == 2
    assert len(resultado.erros) == 2
    # O número da linha aponta para a planilha original, contando o cabeçalho.
    assert {e.numero for e in resultado.erros} == {3, 4}


def test_coluna_de_tipo_define_receita_ou_gasto():
    """A coluna de tipo tem precedência sobre o sinal do valor."""
    csv = (
        b"Data,Descricao,Valor,Tipo\n"
        b"03/04/2026,Entrada,100.00,C\n"
        b"03/04/2026,Saida,100.00,D\n"
    )

    resultado = importacao.ler_planilha("tipos.csv", csv)

    assert resultado.linhas[0].tipo == "Receita"
    assert resultado.linhas[1].tipo == "Gasto"


# --- Leitura de XLSX ---


def _montar_xlsx(linhas: list[list]) -> bytes:
    """Gera um arquivo XLSX em memória a partir de uma lista de linhas.

    Args:
        linhas (list[list]): As linhas, começando pelo cabeçalho.

    Returns:
        bytes: O conteúdo do arquivo.
    """
    from openpyxl import Workbook

    planilha = Workbook()
    aba = planilha.active
    for linha in linhas:
        aba.append(linha)

    buffer = io.BytesIO()
    planilha.save(buffer)
    return buffer.getvalue()


def test_leitura_de_xlsx():
    """Uma planilha XLSX com tipos nativos é lida corretamente."""
    conteudo = _montar_xlsx(
        [
            ["Data", "Descrição", "Valor"],
            [datetime(2026, 4, 3), "MERCADO EXTRA", 250.75],
            [datetime(2026, 4, 4), "UBER TRIP", 32.10],
        ]
    )

    resultado = importacao.ler_planilha("planilha.xlsx", conteudo)

    assert len(resultado.linhas) == 2
    assert resultado.linhas[0].valor == Decimal("250.75")
    assert resultado.linhas[0].categoria_sugerida == "Alimentação"
    assert resultado.linhas[1].categoria_sugerida == "Transporte"


def test_xlsx_corrompido_e_rejeitado():
    """Um arquivo que não é XLSX válido produz erro amigável."""
    with pytest.raises(importacao.ArquivoInvalidoError, match="válida ou está corrompido"):
        importacao.ler_planilha("falso.xlsx", b"isto nao e um xlsx")


# --- Endpoint ---


def test_importacao_via_api(cliente, usuario_com_token):
    """O endpoint importa as transações e devolve o dashboard atualizado."""
    _, csrf = usuario_com_token

    csv = (
        "Data;Descrição;Valor\n"
        "03/04/2026;MERCADO EXTRA;-250,00\n"
        "04/04/2026;UBER TRIP;-30,00\n"
    ).encode()

    resposta = cliente.post(
        "/transacoes/importar",
        params=PERIODO,
        files={"arquivo": ("extrato.csv", csv, "text/csv")},
        headers=cabecalho(csrf),
    )

    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()

    assert corpo["importadas"] == 2
    assert corpo["ignoradas"] == 0
    assert Decimal(corpo["dashboard"]["total_gastos"]) == Decimal("280.00")

    # As transações ficaram vinculadas ao usuário e às categorias adivinhadas.
    transacoes = cliente.get("/transacoes/").json()
    assert len(transacoes) == 2
    assert {t["categoria"]["nome"] for t in transacoes} == {"Alimentação", "Transporte"}


def test_importacao_reporta_erros_por_linha(cliente, usuario_com_token):
    """O relatório aponta a linha e o motivo de cada rejeição."""
    _, csrf = usuario_com_token

    csv = (
        b"Data,Descricao,Valor\n"
        b"03/04/2026,Boa,100.00\n"
        b"xx,Ruim,100.00\n"
    )

    resposta = cliente.post(
        "/transacoes/importar",
        params=PERIODO,
        files={"arquivo": ("misto.csv", csv, "text/csv")},
        headers=cabecalho(csrf),
    )

    corpo = resposta.json()
    assert corpo["importadas"] == 1
    assert corpo["ignoradas"] == 1
    assert corpo["erros"][0]["linha"] == 3


def test_importacao_exige_autenticacao(cliente):
    """Sem sessão, a importação é recusada."""
    resposta = cliente.post(
        "/transacoes/importar",
        params=PERIODO,
        files={"arquivo": ("x.csv", b"Data,Descricao,Valor\n", "text/csv")},
    )
    assert resposta.status_code == 401


def test_importacao_de_arquivo_invalido_retorna_400(cliente, usuario_com_token):
    """Um arquivo fora do padrão retorna erro amigável, não 500."""
    _, csrf = usuario_com_token

    resposta = cliente.post(
        "/transacoes/importar",
        params=PERIODO,
        files={"arquivo": ("ruim.csv", b"a;b\n1;2\n", "text/csv")},
        headers=cabecalho(csrf),
    )

    assert resposta.status_code == 400
    assert "colunas" in resposta.json()["detail"]
