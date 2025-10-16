# Arquivo: backend/schemas.py

from pydantic import BaseModel
from datetime import datetime
import decimal
from typing import Optional 

# --- Schemas para Token ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    nome_usuario: Optional[str] = None
# --- Schemas para Usuário ---

class UsuarioCreate(BaseModel):
    nome_usuario: str
    senha: str

# O que vamos RETORNAR quando lermos um usuário. 
class Usuario(BaseModel):
    id: int
    nome_usuario: str

    class Config:
        from_attributes = True

# --- Schemas para Categoria ---
# O que precisamos para CRIAR uma categoria
class CategoriaCreate(BaseModel):
    nome: str
    tipo: str # "Gasto" ou "Receita"

# O que vamos RETORNAR quando lermos uma categoria do banco
class Categoria(CategoriaCreate):
    id: int

    class Config:
        from_attributes = True


# --- Schemas para Transação (já existentes) ---
class TransacaoCreate(BaseModel):
    descricao: str
    valor: decimal.Decimal
    categoria_id: int
    observacoes: str | None = None

class Transacao(TransacaoCreate):
    id: int
    data: datetime
    usuario_id: int

    class Config:
        from_attributes = True