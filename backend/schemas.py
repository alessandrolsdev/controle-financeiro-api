# Arquivo: backend/schemas.py
"""Módulo de Schemas Pydantic.

Define os modelos de validação de entrada (requests) e serialização de saída
(responses) da API.

Esta camada é a primeira linha de defesa: tudo que chega da rede é considerado
hostil até ser validado aqui. As regras são deliberadamente restritivas —
`extra="forbid"` rejeita campos desconhecidos (impedindo mass assignment), os
valores monetários têm domínio fechado e os campos de texto têm limite de
tamanho para conter abuso de armazenamento.
"""

from __future__ import annotations

import decimal
import re
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

# --- Tipos reutilizáveis com restrição ---

TipoCategoria = Literal["Gasto", "Receita"]

NomeUsuario = Annotated[
    str,
    StringConstraints(min_length=3, max_length=100, strip_whitespace=True),
]

TextoCurto = Annotated[
    str,
    StringConstraints(min_length=1, max_length=255, strip_whitespace=True),
]

TextoLongo = Annotated[str, StringConstraints(max_length=2000)]

# Valor monetário: sempre positivo, com teto coerente com Numeric(14, 2) no
# banco. Sem o teto, um valor maior que a coluna gera erro 500 no driver em vez
# de uma resposta 422 clara.
ValorMonetario = Annotated[
    decimal.Decimal,
    Field(gt=decimal.Decimal("0"), le=decimal.Decimal("999999999999.99")),
]

# Nome de usuário aceita apenas caracteres seguros. Isso elimina de saída uma
# classe inteira de problemas: homoglifos, espaços invisíveis, caracteres de
# controle e tentativas de spoofing visual entre contas.
PADRAO_NOME_USUARIO = re.compile(r"^[a-zA-Z0-9._-]+$")
PADRAO_COR_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Limite superior do intervalo consultável. Sem ele, um pedido de 200 anos
# obriga o banco a varrer e agregar a tabela inteira.
MAXIMO_DIAS_POR_CONSULTA = 1830  # ~5 anos


class SchemaBase(BaseModel):
    """Base comum a todos os schemas de entrada.

    `extra="forbid"` faz a API rejeitar campos desconhecidos em vez de ignorá-los.
    Isso transforma uma tentativa de mass assignment (ex.: enviar `usuario_id`
    ou `token_version` em um payload de perfil) em um erro 422 explícito.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --- SCHEMAS PARA O DASHBOARD ---


class CategoriaDetalhada(BaseModel):
    """Schema auxiliar para dados agregados por categoria.

    Attributes:
        nome_categoria (str): Nome da categoria.
        valor_total (decimal.Decimal): Soma dos valores das transações.
        total_compras (int): Contagem de transações na categoria.
        cor (str): Cor associada à categoria para visualização.
    """

    nome_categoria: str
    valor_total: decimal.Decimal
    total_compras: int  # (Para receitas, isso é 'total_registros')
    cor: str


class DashboardData(BaseModel):
    """Schema de resposta para o endpoint de dashboard.

    Attributes:
        total_receitas (decimal.Decimal): Soma total de receitas.
        total_gastos (decimal.Decimal): Soma total de despesas.
        lucro_liquido (decimal.Decimal): Resultado (receitas - despesas).
        gastos_por_categoria (List[CategoriaDetalhada]): Gastos agrupados.
        receitas_por_categoria (List[CategoriaDetalhada]): Receitas agrupadas.
    """

    total_receitas: decimal.Decimal
    total_gastos: decimal.Decimal
    lucro_liquido: decimal.Decimal
    gastos_por_categoria: list[CategoriaDetalhada]
    receitas_por_categoria: list[CategoriaDetalhada]


# --- SCHEMAS PARA AUTENTICAÇÃO ---


class Token(BaseModel):
    """Schema de resposta contendo o token de acesso.

    Attributes:
        access_token (str): O token JWT gerado.
        token_type (str): Tipo do token (sempre "bearer").
        expires_in (int): Validade do token em segundos.
    """

    access_token: str
    # noqa S105: "bearer" é o nome do esquema de autenticação definido pela
    # RFC 6750, não uma senha embutida no código.
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


class TokenData(BaseModel):
    """Dados extraídos do payload do token JWT.

    Attributes:
        nome_usuario (str): O nome de usuário contido no claim `sub`.
        usuario_id (Optional[int]): O ID contido no claim `uid`.
        token_version (int): A versão de credenciais do claim `ver`.
        jti (Optional[str]): O identificador único do token.
    """

    nome_usuario: str
    usuario_id: int | None = None
    token_version: int = 0
    jti: str | None = None


# --- SCHEMAS PARA USUÁRIO ---


class UsuarioCreate(SchemaBase):
    """Schema de entrada para criação de um novo usuário.

    Attributes:
        nome_usuario (str): Nome de usuário desejado.
        senha (str): Senha em texto plano, validada contra a política de força.
    """

    nome_usuario: NomeUsuario
    # O tamanho mínimo espelha a política em `security.TAMANHO_MINIMO_SENHA`;
    # a validação completa (senhas comuns, variedade) roda no endpoint.
    senha: Annotated[str, StringConstraints(min_length=12, max_length=1024)]

    @field_validator("nome_usuario")
    @classmethod
    def _validar_nome_usuario(cls, valor: str) -> str:
        """Restringe o nome de usuário a caracteres seguros.

        Args:
            valor (str): O nome informado.

        Raises:
            ValueError: Se contiver caracteres fora do conjunto permitido.

        Returns:
            str: O nome validado.
        """
        if not PADRAO_NOME_USUARIO.match(valor):
            raise ValueError(
                "O nome de usuário deve conter apenas letras, números, "
                "ponto, hífen e sublinhado."
            )
        return valor


class Usuario(BaseModel):
    """Schema de resposta com detalhes do usuário.

    Note que `senha_hash` e `token_version` não estão declarados: campos
    ausentes do schema de resposta nunca são serializados, mesmo que existam
    no objeto ORM de origem.

    Attributes:
        id (int): ID do usuário.
        nome_usuario (str): Nome de usuário.
        criado_em (datetime): Data de criação da conta.
        nome_completo (Optional[str]): Nome completo do usuário.
        data_nascimento (Optional[date]): Data de nascimento.
        avatar_url (Optional[str]): URL do avatar.
        email (Optional[EmailStr]): Endereço de email.
    """

    id: int
    nome_usuario: str
    criado_em: datetime

    # Campos de Perfil
    nome_completo: str | None = None
    data_nascimento: date | None = None
    avatar_url: str | None = None
    email: EmailStr | None = None

    model_config = ConfigDict(from_attributes=True)


class UsuarioUpdate(SchemaBase):
    """Schema de entrada para atualização de dados do usuário.

    Attributes:
        nome_usuario (Optional[str]): Novo nome de usuário.
        nome_completo (Optional[str]): Novo nome completo.
        data_nascimento (Optional[date]): Nova data de nascimento.
        avatar_url (Optional[str]): Nova URL de avatar.
        email (Optional[EmailStr]): Novo email.
    """

    nome_usuario: NomeUsuario | None = None
    nome_completo: Annotated[str, StringConstraints(max_length=255)] | None = None
    data_nascimento: date | None = None
    avatar_url: Annotated[str, StringConstraints(max_length=2000)] | None = None
    email: EmailStr | None = None

    @field_validator("nome_usuario")
    @classmethod
    def _validar_nome_usuario(cls, valor: str | None) -> str | None:
        """Aplica a mesma restrição de caracteres do cadastro.

        Args:
            valor (Optional[str]): O nome informado.

        Raises:
            ValueError: Se contiver caracteres fora do conjunto permitido.

        Returns:
            Optional[str]: O nome validado.
        """
        if valor is not None and not PADRAO_NOME_USUARIO.match(valor):
            raise ValueError(
                "O nome de usuário deve conter apenas letras, números, "
                "ponto, hífen e sublinhado."
            )
        return valor

    @field_validator("data_nascimento")
    @classmethod
    def _validar_data_nascimento(cls, valor: date | None) -> date | None:
        """Rejeita datas de nascimento impossíveis.

        Args:
            valor (Optional[date]): A data informada.

        Raises:
            ValueError: Se a data estiver no futuro ou for absurdamente antiga.

        Returns:
            Optional[date]: A data validada.
        """
        if valor is None:
            return None
        hoje = datetime.now(UTC).date()
        if valor > hoje:
            raise ValueError("A data de nascimento não pode estar no futuro.")
        if valor.year < 1900:
            raise ValueError("A data de nascimento é inválida.")
        return valor

    @field_validator("avatar_url")
    @classmethod
    def _validar_avatar_url(cls, valor: str | None) -> str | None:
        """Restringe a URL de avatar a esquemas seguros.

        O campo é renderizado pelo frontend em um atributo `src`. Sem esta
        checagem, um valor `javascript:` ou `data:text/html` vira um vetor de
        XSS armazenado.

        Args:
            valor (Optional[str]): A URL informada.

        Raises:
            ValueError: Se o esquema não for https, ou data:image.

        Returns:
            Optional[str]: A URL validada.
        """
        if valor is None or valor == "":
            return valor

        normalizada = valor.strip().lower()

        if normalizada.startswith("https://"):
            return valor
        if normalizada.startswith("data:image/"):
            return valor

        raise ValueError(
            "A URL do avatar deve usar https:// ou ser uma imagem embutida "
            "(data:image/...)."
        )


class UsuarioChangePassword(SchemaBase):
    """Schema de entrada para alteração de senha.

    Attributes:
        senha_antiga (str): A senha atual do usuário.
        senha_nova (str): A nova senha desejada.
    """

    senha_antiga: Annotated[str, StringConstraints(min_length=1, max_length=1024)]
    senha_nova: Annotated[str, StringConstraints(min_length=12, max_length=1024)]

    @model_validator(mode="after")
    def _senhas_devem_diferir(self) -> UsuarioChangePassword:
        """Impede que a "nova" senha seja idêntica à atual.

        Raises:
            ValueError: Se as senhas forem iguais.

        Returns:
            UsuarioChangePassword: A própria instância validada.
        """
        if self.senha_antiga == self.senha_nova:
            raise ValueError("A nova senha deve ser diferente da senha atual.")
        return self


# --- SCHEMAS PARA CATEGORIA ---


class CategoriaCreate(SchemaBase):
    """Schema de entrada para criação de categoria.

    Attributes:
        nome (str): Nome da categoria.
        tipo (TipoCategoria): "Gasto" ou "Receita".
        cor (str): Cor em formato hexadecimal #RRGGBB.
    """

    nome: Annotated[
        str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)
    ]
    # Domínio fechado. Antes era `str` livre: uma categoria criada como
    # "Despesa" era aceita mas nunca somada pelo dashboard, que só reconhece
    # "Gasto" e "Receita" — os valores sumiam do relatório sem qualquer erro.
    tipo: TipoCategoria
    cor: str = "#CCCCCC"

    @field_validator("cor")
    @classmethod
    def _validar_cor(cls, valor: str) -> str:
        """Garante que a cor está no formato hexadecimal #RRGGBB.

        Args:
            valor (str): A cor informada.

        Raises:
            ValueError: Se o formato for inválido.

        Returns:
            str: A cor validada.
        """
        if not PADRAO_COR_HEX.match(valor):
            raise ValueError("A cor deve estar no formato hexadecimal #RRGGBB.")
        return valor


class Categoria(BaseModel):
    """Schema de resposta para detalhes da categoria.

    Attributes:
        id (int): ID da categoria.
        nome (str): Nome da categoria.
        tipo (TipoCategoria): Tipo da categoria.
        cor (str): Cor da categoria.
    """

    id: int
    nome: str
    tipo: TipoCategoria
    cor: str

    model_config = ConfigDict(from_attributes=True)


class CategoriaUpdate(SchemaBase):
    """Schema de entrada para atualização de categoria.

    Attributes:
        nome (Optional[str]): Novo nome.
        tipo (Optional[TipoCategoria]): Novo tipo.
        cor (Optional[str]): Nova cor.
    """

    nome: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] | None = None
    tipo: TipoCategoria | None = None
    cor: str | None = None

    @field_validator("cor")
    @classmethod
    def _validar_cor(cls, valor: str | None) -> str | None:
        """Garante o formato hexadecimal quando a cor é informada.

        Args:
            valor (Optional[str]): A cor informada.

        Raises:
            ValueError: Se o formato for inválido.

        Returns:
            Optional[str]: A cor validada.
        """
        if valor is not None and not PADRAO_COR_HEX.match(valor):
            raise ValueError("A cor deve estar no formato hexadecimal #RRGGBB.")
        return valor

    @model_validator(mode="after")
    def _exigir_ao_menos_um_campo(self) -> CategoriaUpdate:
        """Rejeita um payload de atualização inteiramente vazio.

        Raises:
            ValueError: Se nenhum campo tiver sido informado.

        Returns:
            CategoriaUpdate: A própria instância validada.
        """
        if self.nome is None and self.tipo is None and self.cor is None:
            raise ValueError("Informe ao menos um campo para atualizar.")
        return self


# --- SCHEMAS PARA TRANSAÇÃO ---


class TransacaoCreate(SchemaBase):
    """Schema de entrada para criação ou atualização de transação.

    Attributes:
        descricao (str): Descrição da transação.
        valor (decimal.Decimal): Valor da transação, sempre positivo.
        categoria_id (int): ID da categoria associada (deve pertencer ao usuário).
        data (datetime): Data e hora da transação.
        observacoes (Optional[str]): Observações adicionais.
    """

    descricao: TextoCurto
    valor: ValorMonetario
    categoria_id: int = Field(gt=0)
    data: datetime
    observacoes: TextoLongo | None = None

    @field_validator("valor")
    @classmethod
    def _normalizar_valor(cls, valor: decimal.Decimal) -> decimal.Decimal:
        """Quantiza o valor para duas casas decimais.

        A coluna é `Numeric(14, 2)`. Sem a quantização explícita, um valor com
        mais casas seria arredondado pelo banco de forma dependente do dialeto —
        um comportamento inaceitável para dinheiro.

        Args:
            valor (decimal.Decimal): O valor informado.

        Raises:
            ValueError: Se o valor não for finito.

        Returns:
            decimal.Decimal: O valor com exatamente duas casas decimais.
        """
        if not valor.is_finite():
            raise ValueError("O valor precisa ser um número finito.")
        # ROUND_HALF_UP é a convenção contábil usual no Brasil.
        return valor.quantize(
            decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP
        )

    @field_validator("data")
    @classmethod
    def _validar_data(cls, valor: datetime) -> datetime:
        """Normaliza a data para UTC e rejeita datas implausíveis.

        Args:
            valor (datetime): A data informada.

        Raises:
            ValueError: Se a data for muito antiga ou muito no futuro.

        Returns:
            datetime: A data normalizada em UTC.
        """
        # Datas sem fuso são interpretadas como UTC para manter os relatórios
        # consistentes independentemente do fuso do cliente.
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=UTC)
        else:
            valor = valor.astimezone(UTC)

        agora = datetime.now(UTC)

        # Uma folga de um dia acomoda clientes com relógio adiantado e fusos
        # à frente do UTC, sem permitir lançamentos em datas arbitrárias.
        if valor > agora + timedelta(days=1):
            raise ValueError("A data da transação não pode estar no futuro.")

        if valor.year < 1970:
            raise ValueError("A data da transação é anterior ao limite suportado.")

        return valor


class Transacao(BaseModel):
    """Schema de resposta para detalhes da transação.

    Attributes:
        id (int): ID da transação.
        descricao (str): Descrição da transação.
        valor (decimal.Decimal): Valor da transação.
        data (datetime): Data e hora da transação.
        observacoes (Optional[str]): Observações adicionais.
        categoria_id (int): ID da categoria associada.
        usuario_id (int): ID do usuário proprietário.
        categoria (Categoria): Objeto com detalhes da categoria associada.
    """

    id: int
    descricao: str
    valor: decimal.Decimal
    data: datetime
    observacoes: str | None = None
    categoria_id: int
    usuario_id: int

    categoria: Categoria

    model_config = ConfigDict(from_attributes=True)


# --- SCHEMAS PARA RELATÓRIOS ---


class PontoDeTendencia(BaseModel):
    """Representa um ponto de dados em um gráfico de tendência.

    Attributes:
        data (date | str): Data ou hora do ponto.
        valor (decimal.Decimal): Valor acumulado no ponto.
    """

    data: date | str
    valor: decimal.Decimal


class DadosDeTendencia(BaseModel):
    """Schema de resposta para dados de gráficos de tendência.

    Attributes:
        receitas (List[PontoDeTendencia]): Série de dados para receitas.
        despesas (List[PontoDeTendencia]): Série de dados para despesas.
    """

    receitas: list[PontoDeTendencia]
    despesas: list[PontoDeTendencia]


class MensagemDeSucesso(BaseModel):
    """Resposta genérica de confirmação de operação.

    Attributes:
        message (str): Descrição do resultado.
    """

    message: str
