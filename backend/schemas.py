# Arquivo: backend/schemas.py (VERSÃO V7.2 - COMPLETA)
"""
CHECK-UP (V7.2): Adiciona 'nome_usuario' ao 'UsuarioUpdate'.
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime, date
import decimal
from typing import Optional, List

# --- 1. SCHEMAS (Dashboard) ---
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

# --- 2. SCHEMAS (Auth) ---
class Token(BaseModel):
    access_token: str
    token_type: str
class TokenData(BaseModel):
    nome_usuario: Optional[str] = None

# --- 3. SCHEMAS (Usuário) ---
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
    """Schema de ENTRADA para atualizar o perfil."""
    # O NOVO CAMPO (V7.2)
    nome_usuario: Optional[str] = None 
    
    nome_completo: Optional[str] = None
    data_nascimento: Optional[date] = None
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None

class UsuarioChangePassword(BaseModel):
    senha_antiga: str
    senha_nova: str

# --- (Restante dos schemas, Categoria, Transacao, etc.) ---
# --- 4. SCHEMAS PARA CATEGORIA ---
class CategoriaCreate(BaseModel):
    nome: str
    tipo: str
    cor: str = "#CCCCCC"
class Categoria(CategoriaCreate):
    id: int
    model_config = {'from_attributes': True}
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