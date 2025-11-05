# Arquivo: backend/schemas.py (VERSÃO FINAL CORRIGIDA PARA Pydantic V2)
# Responsabilidade: Definir os "Contratos" de dados da nossa API.

from pydantic import BaseModel
from datetime import datetime, date
import decimal
from typing import Optional, List

# --- 1. SCHEMAS PARA O DASHBOARD ---

class GastoPorCategoria(BaseModel):
    """Schema auxiliar para os dados do dashboard."""
    nome_categoria: str
    valor_total: decimal.Decimal
    total_compras: int

    # Sintaxe MODERNA (Pydantic V2) para 'from_attributes = True'
    # Esta é a "cola mágica" que permite ao Pydantic ler dados
    # de um objeto do SQLAlchemy (ex: models.Categoria).
    model_config = {'from_attributes': True}

class DashboardData(BaseModel):
    """Schema de RESPOSTA para o endpoint /dashboard/."""
    total_receitas: decimal.Decimal
    total_gastos: decimal.Decimal
    lucro_liquido: decimal.Decimal
    gastos_por_categoria: List[GastoPorCategoria]


# --- 2. SCHEMAS PARA AUTENTICAÇÃO (Tokens) ---

class Token(BaseModel):
    """Schema de RESPOSTA para o endpoint /token."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Schema que define os dados ARMAZENADOS DENTRO do Token JWT."""
    nome_usuario: Optional[str] = None


# --- 3. SCHEMAS PARA USUÁRIO ---

class UsuarioCreate(BaseModel):
    """Schema de ENTRADA (criação) para um novo usuário."""
    nome_usuario: str
    senha: str # Recebe a senha em texto plano, que será hasheada pelo 'crud.py'

class Usuario(BaseModel):
    """Schema de RESPOSTA (leitura) para um usuário."""
    id: int
    nome_usuario: str
    criado_em: datetime

    model_config = {'from_attributes': True}


# --- 4. SCHEMAS PARA CATEGORIA ---

class CategoriaCreate(BaseModel):
    """Schema de ENTRADA (criação) para uma nova categoria."""
    nome: str
    tipo: str # "Gasto" ou "Receita"

class Categoria(CategoriaCreate):
    """Schema de RESPOSTA (leitura) para uma categoria."""
    id: int

    model_config = {'from_attributes': True}


# --- 5. SCHEMAS PARA TRANSAÇÃO ---

class TransacaoCreate(BaseModel):
    """
    Schema de ENTRADA (criação) para uma nova transação.
    É o que o formulário do modal envia.
    """
    descricao: str
    valor: decimal.Decimal
    categoria_id: int
    data: date # O usuário envia apenas a data (AAAA-MM-DD)
    observacoes: str | None = None # Sintaxe moderna para 'Optional[str]'


class Transacao(TransacaoCreate):
    """
    Schema de RESPOSTA (leitura) para uma transação.
    Usado quando listamos as transações.
    """
    id: int
    # Sobrescrevemos 'data' para retornar um 'datetime' completo
    data: datetime 
    usuario_id: int

    # Precisamos incluir o objeto Categoria completo aqui
    # para que nossa lista de "Transações Recentes" funcione!
    categoria: Categoria 

    model_config = {'from_attributes': True}