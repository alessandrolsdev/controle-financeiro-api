# Arquivo: backend/models.py
"""
Módulo de Modelos (Models) - A "Planta" do Banco de Dados.

Este arquivo define a ESTRUTURA de todas as tabelas no banco de dados
usando a sintaxe moderna do SQLAlchemy 2.0 (ORM Declarativo com Mapped).

Cada classe aqui representa uma tabela no PostgreSQL (produção)
ou SQLite (desenvolvimento).
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, func, Date
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

# Importa a Base declarativa que criamos no arquivo database.py
from .database import Base


# --- 1. MODELO DA TABELA DE USUÁRIOS ---
class Usuario(Base):
    """
    Representa a tabela 'usuarios'.
    Este é o "dono" das transações financeiras e o
    objeto principal de autenticação.
    """
    __tablename__ = "usuarios"

    # Coluna Primária
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # --- Informações de Autenticação ---
    nome_usuario: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # --- Campos de Perfil (V7.0+) ---
    nome_completo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    data_nascimento: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadados
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # --- Relacionamento (O "link" do Python) ---
    # Define o 'lado um' do relacionamento 'Um-para-Muitos'
    # (Um 'Usuario' tem Muitas 'Transacoes')
    # Permite acessar 'meu_usuario.transacoes'
    # 'lazy="selectin"' é uma otimização de performance moderna.
    transacoes: Mapped[List["Transacao"]] = relationship(
        back_populates="proprietario", lazy="selectin"
    )


# --- 2. MODELO DA TABELA DE CATEGORIAS ---
class Categoria(Base):
    """
    Representa a tabela 'categorias'.
    Usada para classificar transações (ex: "Combustível", "Salário").
    """
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    
    # Define se a categoria é uma "Gasto" (Despesa) ou "Receita" (Ganho)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # O código HEX da cor (V5.0)
    cor: Mapped[str] = mapped_column(String(7), nullable=False, default="#CCCCCC") 

    # Define o 'lado um' do relacionamento 'Um-para-Muitos'
    # (Uma 'Categoria' tem Muitas 'Transacoes')
    transacoes: Mapped[List["Transacao"]] = relationship(
        back_populates="categoria", lazy="selectin"
    )


# --- 3. MODELO DA TABELA DE TRANSAÇÕES (O CORAÇÃO DO SISTEMA) ---
class Transacao(Base):
    """
    Representa a tabela 'transacoes'.
    Um único registro financeiro (um gasto ou um ganho).
    """
    __tablename__ = "transacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Decisão de Engenharia:
    # Usamos 'Numeric' (Decimal) em vez de 'Float' para
    # garantir precisão absoluta em cálculos financeiros.
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Usamos 'DateTime' para capturar a hora exata da transação (V2.2)
    data: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # 'Text' permite notas mais longas do que 'String'
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Chaves Estrangeiras (Foreign Keys) ---
    # (Os "links" físicos entre as tabelas)
    
    # Garante que 'categoria_id' DEVE apontar para uma 'categorias.id'
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"), nullable=False)
    
    # Garante que 'usuario_id' DEVE apontar para um 'usuarios.id'
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)

    # --- Relacionamentos (Os "links" do Python) ---
    
    # Define o 'lado muitos' do relacionamento 'Muitos-para-Um'
    # Permite acessar 'minha_transacao.categoria'
    # (lazy="select" é o padrão, 'lazy="joined"' foi removido na V-Revert)
    categoria: Mapped["Categoria"] = relationship(
        back_populates="transacoes"
    )
    
    # Permite acessar 'minha_transacao.proprietario'
    proprietario: Mapped["Usuario"] = relationship(
        back_populates="transacoes"
    )