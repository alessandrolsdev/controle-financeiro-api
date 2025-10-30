# Arquivo: backend/schemas.py (Versão Completa e Final)

from pydantic import BaseModel
from datetime import datetime, date
import decimal
from typing import Optional, List

# --- 1. SCHEMAS PARA O DASHBOARD ---

class GastoPorCategoria(BaseModel):
    """Schema para representar o total de gastos de uma única categoria."""
    nome_categoria: str
    valor_total: decimal.Decimal

    class Config:
        from_attributes = True

class DashboardData(BaseModel):
    """Schema principal de resposta para o endpoint /dashboard/."""
    total_receitas: decimal.Decimal
    total_gastos: decimal.Decimal
    lucro_liquido: decimal.Decimal
    gastos_por_categoria: List[GastoPorCategoria]


# --- 2. SCHEMAS PARA AUTENTICAÇÃO (Tokens) ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    nome_usuario: Optional[str] = None


# --- 3. SCHEMAS PARA USUÁRIO ---

class UsuarioCreate(BaseModel):
    """Dados necessários para criar um novo usuário."""
    nome_usuario: str
    senha: str

class Usuario(BaseModel):
    """Dados retornados ao listar um usuário (NUNCA a senha)."""
    id: int
    nome_usuario: str
    criado_em: datetime # Adiciona a data de criação para dashboards

    class Config:
        from_attributes = True


# --- 4. SCHEMAS PARA CATEGORIA ---

class CategoriaCreate(BaseModel):
    """Dados necessários para criar uma nova categoria."""
    nome: str
    tipo: str # "Gasto" ou "Receita"

class Categoria(CategoriaCreate):
    """Dados retornados ao listar uma categoria."""
    id: int

    class Config:
        from_attributes = True


# --- 5. SCHEMAS PARA TRANSAÇÃO ---

class TransacaoCreate(BaseModel):
    """Dados necessários para criar uma nova transação (o Frontend envia isso)."""
    descricao: str
    valor: decimal.Decimal
    categoria_id: int
    observacoes: str | None = None # | None é a sintaxe moderna para Optional

class Transacao(TransacaoCreate):
    """Dados retornados ao listar uma transação."""
    id: int
    data: datetime
    usuario_id: int

    class Config:
        from_attributes = True