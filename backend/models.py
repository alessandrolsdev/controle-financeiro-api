# Arquivo: backend/models.py (VERSÃO COMPLETA V7.1)
"""
CHECK-UP (V7.1): Adiciona o novo campo 'email' à tabela 'Usuario'.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, func, Date
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from .database import Base


# --- 1. MODELO DA TABELA DE USUÁRIOS (ATUALIZADO) ---
class Usuario(Base):
    __tablename__ = "usuarios"

    # --- Campos Antigos ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome_usuario: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # --- Campos de Perfil (V7.0) ---
    nome_completo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    data_nascimento: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- NOVO CAMPO DE EMAIL (V7.1) ---
    # (Opcional, mas 'unique=True' garante que não haja 2 contas com o mesmo email)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)

    # --- Relacionamento (Sem mudança) ---
    transacoes: Mapped[List["Transacao"]] = relationship(
        back_populates="proprietario", lazy="selectin"
    )

# ... (Restante do 'models.py' - Categoria e Transacao - sem mudança) ...
# --- 2. MODELO DA TABELA DE CATEGORIAS ---
class Categoria(Base):
    __tablename__ = "categorias"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    cor: Mapped[str] = mapped_column(String(7), nullable=False, default="#CCCCCC") 
    transacoes: Mapped[List["Transacao"]] = relationship(
        back_populates="categoria", lazy="selectin"
    )

# --- 3. MODELO DA TABELA DE TRANSAÇÕES ---
class Transacao(Base):
    __tablename__ = "transacoes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    categoria: Mapped["Categoria"] = relationship(
        back_populates="transacoes"
    )
    proprietario: Mapped["Usuario"] = relationship(
        back_populates="transacoes"
    )