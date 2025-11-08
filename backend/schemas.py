# Arquivo: backend/schemas.py (VERSÃO COMPLETA V8.0 - COM 'CategoriaUpdate')
"""
CHECK-UP (V8.0): Adiciona o novo schema 'CategoriaUpdate'
para permitir a edição parcial (PATCH) de uma categoria.
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime, date
import decimal
from typing import Optional, List

# --- 1. SCHEMAS PARA O DASHBOARD ---
class CategoriaDetalhada(BaseModel):
    nome_categoria: str
    valor_total: decimal.Decimal
    total_compras: int 
    cor: str
class DashboardData(BaseModel):
    total_receitas: decimal.Decimal
    total_gastos: decimal.Decimal
    lucro_liquido: decimal.Decimal
    gastos_por_categoria: List[CategoriaDetalhada] 
    receitas_por_categoria: List[CategoriaDetalhada]

# --- 2. SCHEMAS PARA AUTENTICAÇÃO (Tokens) ---
class Token(BaseModel):
    access_token: str
    token_type: str
class TokenData(BaseModel):
    nome_usuario: Optional[str] = None

# --- 3. SCHEMAS PARA USUÁRIO ---
class UsuarioCreate(BaseModel):
    nome_usuario: str
    senha: str
class Usuario(BaseModel):
    id: int
    nome_usuario: str
    criado_em: datetime
    nome_completo: Optional[str] = None
    data_nascimento: Optional[date] = None
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None 
    model_config = {'from_attributes': True}
class UsuarioUpdate(BaseModel):
    nome_usuario: Optional[str] = None 
    nome_completo: Optional[str] = None
    data_nascimento: Optional[date] = None
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None
class UsuarioChangePassword(BaseModel):
    senha_antiga: str
    senha_nova: str

# --- 4. SCHEMAS PARA CATEGORIA (ATUALIZADO) ---
class CategoriaCreate(BaseModel):
    nome: str
    tipo: str # "Gasto" ou "Receita"
    cor: str = "#CCCCCC"
class Categoria(CategoriaCreate):
    id: int
    model_config = {'from_attributes': True}

# O NOVO SCHEMA (V8.0)
class CategoriaUpdate(BaseModel):
    """
    Schema para atualização parcial. O usuário pode enviar
    só o nome, só o tipo, ou só a cor.
    """
    nome: Optional[str] = None
    tipo: Optional[str] = None
    cor: Optional[str] = None

# --- 5. SCHEMAS PARA TRANSAÇÃO ---
class TransacaoCreate(BaseModel):
    descricao: str
    valor: decimal.Decimal
    categoria_id: int
    data: datetime 
    observacoes: str | None = None
class Transacao(TransacaoCreate):
    id: int
    data: datetime 
    usuario_id: int
    categoria: Categoria 
    model_config = {'from_attributes': True}
    
# --- 6. SCHEMAS PARA RELATÓRIOS ---
class PontoDeTendencia(BaseModel):
    data: date | str
    valor: decimal.Decimal
class DadosDeTendencia(BaseModel):
    receitas: List[PontoDeTendencia]
    despesas: List[PontoDeTendencia]