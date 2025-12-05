# Arquivo: backend/schemas.py
"""Módulo de Schemas Pydantic.

Este módulo define os modelos Pydantic utilizados para validação de dados
de entrada (requests) e serialização de dados de saída (responses) da API.

Garante a integridade e consistência dos dados que transitam entre o frontend
e o backend.

Classes:
    CategoriaDetalhada: Schema auxiliar para agregação de dados de categorias.
    DashboardData: Schema de resposta com resumo financeiro para o dashboard.
    Token: Schema de resposta contendo o token de acesso JWT.
    TokenData: Schema com dados decodificados do token JWT.
    UsuarioCreate: Schema de entrada para criação de usuário.
    Usuario: Schema de resposta para detalhes do usuário.
    UsuarioUpdate: Schema de entrada para atualização de perfil de usuário.
    UsuarioChangePassword: Schema de entrada para alteração de senha.
    CategoriaCreate: Schema de entrada para criação de categoria.
    Categoria: Schema de resposta para detalhes da categoria.
    CategoriaUpdate: Schema de entrada para atualização de categoria.
    TransacaoCreate: Schema de entrada para criação de transação.
    Transacao: Schema de resposta para detalhes da transação.
    PontoDeTendencia: Schema para pontos de dados em gráficos.
    DadosDeTendencia: Schema de resposta para dados de gráficos de tendência.
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime, date
import decimal
from typing import Optional, List

# --- SCHEMAS PARA O DASHBOARD ---

class CategoriaDetalhada(BaseModel):
    """Schema auxiliar para dados agregados por categoria.

    Usado em respostas de dashboard e relatórios para apresentar totais
    por categoria.

    Attributes:
        nome_categoria (str): Nome da categoria.
        valor_total (decimal.Decimal): Soma dos valores das transações da categoria.
        total_compras (int): Contagem de transações na categoria.
        cor (str): Cor associada à categoria para visualização.
    """
    nome_categoria: str
    valor_total: decimal.Decimal
    total_compras: int # (Para receitas, isso é 'total_registros')
    cor: str

class DashboardData(BaseModel):
    """Schema de resposta para o endpoint de dashboard.

    Contém o resumo financeiro consolidado.

    Attributes:
        total_receitas (decimal.Decimal): Soma total de receitas.
        total_gastos (decimal.Decimal): Soma total de despesas.
        lucro_liquido (decimal.Decimal): Resultado (receitas - despesas).
        gastos_por_categoria (List[CategoriaDetalhada]): Lista de gastos agrupados por categoria.
        receitas_por_categoria (List[CategoriaDetalhada]): Lista de receitas agrupadas por categoria.
    """
    total_receitas: decimal.Decimal
    total_gastos: decimal.Decimal
    lucro_liquido: decimal.Decimal
    gastos_por_categoria: List[CategoriaDetalhada] 
    receitas_por_categoria: List[CategoriaDetalhada]


# --- SCHEMAS PARA AUTENTICAÇÃO ---

class Token(BaseModel):
    """Schema de resposta contendo o token de acesso.

    Attributes:
        access_token (str): O token JWT gerado.
        token_type (str): Tipo do token (geralmente "bearer").
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Dados extraídos do payload do token JWT.

    Attributes:
        nome_usuario (Optional[str]): O nome de usuário (subject) contido no token.
    """
    nome_usuario: Optional[str] = None


# --- SCHEMAS PARA USUÁRIO ---

class UsuarioCreate(BaseModel):
    """Schema de entrada para criação de um novo usuário.

    Attributes:
        nome_usuario (str): Nome de usuário desejado.
        senha (str): Senha em texto plano.
    """
    nome_usuario: str
    senha: str

class Usuario(BaseModel):
    """Schema de resposta com detalhes do usuário.

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
    nome_completo: Optional[str] = None
    data_nascimento: Optional[date] = None
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None 

    model_config = {'from_attributes': True}


class UsuarioUpdate(BaseModel):
    """Schema de entrada para atualização de dados do usuário (PATCH).

    Attributes:
        nome_usuario (Optional[str]): Novo nome de usuário.
        nome_completo (Optional[str]): Novo nome completo.
        data_nascimento (Optional[date]): Nova data de nascimento.
        avatar_url (Optional[str]): Nova URL de avatar.
        email (Optional[EmailStr]): Novo email.
    """
    nome_usuario: Optional[str] = None 
    nome_completo: Optional[str] = None
    data_nascimento: Optional[date] = None
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None

class UsuarioChangePassword(BaseModel):
    """Schema de entrada para alteração de senha.

    Attributes:
        senha_antiga (str): A senha atual do usuário.
        senha_nova (str): A nova senha desejada.
    """
    senha_antiga: str
    senha_nova: str

# --- SCHEMAS PARA CATEGORIA ---

class CategoriaCreate(BaseModel):
    """Schema de entrada para criação de categoria.

    Attributes:
        nome (str): Nome da categoria.
        tipo (str): Tipo da categoria ("Despesa" ou "Receita").
        cor (str): Cor em formato hexadecimal. Padrão: "#CCCCCC".
    """
    nome: str
    tipo: str
    cor: str = "#CCCCCC"

class Categoria(CategoriaCreate):
    """Schema de resposta para detalhes da categoria.

    Attributes:
        id (int): ID da categoria.
        nome (str): Nome da categoria.
        tipo (str): Tipo da categoria.
        cor (str): Cor da categoria.
    """
    id: int
    model_config = {'from_attributes': True}

class CategoriaUpdate(BaseModel):
    """Schema de entrada para atualização de categoria.

    Attributes:
        nome (Optional[str]): Novo nome.
        tipo (Optional[str]): Novo tipo.
        cor (Optional[str]): Nova cor.
    """
    nome: Optional[str] = None
    tipo: Optional[str] = None
    cor: Optional[str] = None

# --- SCHEMAS PARA TRANSAÇÃO ---

class TransacaoCreate(BaseModel):
    """Schema de entrada para criação ou atualização de transação.

    Attributes:
        descricao (str): Descrição da transação.
        valor (decimal.Decimal): Valor da transação.
        categoria_id (int): ID da categoria associada.
        data (datetime): Data e hora da transação.
        observacoes (Optional[str]): Observações adicionais.
    """
    descricao: str
    valor: decimal.Decimal
    categoria_id: int
    data: datetime
    observacoes: str | None = None

class Transacao(TransacaoCreate):
    """Schema de resposta para detalhes da transação.

    Attributes:
        id (int): ID da transação.
        usuario_id (int): ID do usuário proprietário.
        categoria (Categoria): Objeto com detalhes da categoria associada.
    """
    id: int
    usuario_id: int
    
    categoria: Categoria 
    
    model_config = {'from_attributes': True}
    
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
    """Schema de resposta para dados consolidados de gráficos de tendência.

    Attributes:
        receitas (List[PontoDeTendencia]): Série de dados para receitas.
        despesas (List[PontoDeTendencia]): Série de dados para despesas.
    """
    receitas: List[PontoDeTendencia]
    despesas: List[PontoDeTendencia]
