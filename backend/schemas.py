# Arquivo: backend/schemas.py (Versão Completa e Final)
from pydantic import BaseModel
from datetime import datetime, date
import decimal
from typing import Optional, List

# --- 1. SCHEMAS PARA O DASHBOARD ---
class GastoPorCategoria(BaseModel):
    nome_categoria: str
    valor_total: decimal.Decimal
    class Config:
        from_attributes = True

class DashboardData(BaseModel):
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
    nome_usuario: str
    senha: str

class Usuario(BaseModel):
    id: int
    nome_usuario: str
    criado_em: datetime
    class Config:
        from_attributes = True

# --- 4. SCHEMAS PARA CATEGORIA ---
class CategoriaCreate(BaseModel):
    nome: str
    tipo: str # "Gasto" ou "Receita"

class Categoria(CategoriaCreate):
    id: int
    class Config:
        from_attributes = True

# --- 5. SCHEMAS PARA TRANSAÇÃO ---
class TransacaoCreate(BaseModel):
    descricao: str
    valor: decimal.Decimal
    categoria_id: int
    data: date
    observacoes: str | None = None

class Transacao(TransacaoCreate):
    id: int
    data: datetime
    usuario_id: int
    class Config:
        from_attributes = True