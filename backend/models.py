# Arquivo: backend/models.py
"""Módulo de Definição dos Modelos ORM (Object-Relational Mapping).

Este módulo define a estrutura das tabelas do banco de dados utilizando a
sintaxe declarativa moderna do SQLAlchemy 2.0 (Mapped e mapped_column).
As classes aqui definidas mapeiam diretamente para as tabelas 'usuarios',
'categorias' e 'transacoes' no banco de dados.

Classes:
    Usuario: Modelo para a tabela de usuários do sistema.
    Categoria: Modelo para a tabela de categorias de transações.
    Transacao: Modelo para a tabela de transações financeiras.
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, func, Date
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from .database import Base


class Usuario(Base):
    """Representa um usuário do sistema na tabela 'usuarios'.

    Armazena informações de autenticação (nome de usuário, senha hash) e
    dados de perfil (nome completo, email, avatar).

    Attributes:
        id (int): Identificador único do usuário (Chave Primária).
        nome_usuario (str): Nome de usuário único para login.
        senha_hash (str): Hash da senha do usuário para autenticação segura.
        nome_completo (Optional[str]): Nome completo do usuário.
        email (Optional[str]): Endereço de email do usuário (único).
        data_nascimento (Optional[datetime]): Data de nascimento do usuário.
        avatar_url (Optional[str]): URL para a imagem de avatar do usuário.
        criado_em (datetime): Data e hora de criação do registro.
        transacoes (List[Transacao]): Relacionamento com as transações do usuário.
    """
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # --- Informações de Autenticação ---
    nome_usuario: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # --- Campos de Perfil ---
    nome_completo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    data_nascimento: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadados
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    transacoes: Mapped[List["Transacao"]] = relationship(
        back_populates="proprietario", lazy="selectin"
    )


class Categoria(Base):
    """Representa uma categoria de transação na tabela 'categorias'.

    Categorias são usadas para classificar transações (ex: Alimentação, Transporte)
    e possuem um tipo (Despesa ou Receita) e uma cor para exibição.

    Attributes:
        id (int): Identificador único da categoria (Chave Primária).
        nome (str): Nome da categoria.
        tipo (str): Tipo da categoria ('Despesa' ou 'Receita').
        cor (str): Código hexadecimal da cor associada à categoria (ex: '#FF0000').
        transacoes (List[Transacao]): Relacionamento com as transações desta categoria.
    """
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    cor: Mapped[str] = mapped_column(String(7), nullable=False, default="#CCCCCC") 

    # Relacionamentos
    transacoes: Mapped[List["Transacao"]] = relationship(
        back_populates="categoria", lazy="selectin"
    )


class Transacao(Base):
    """Representa uma transação financeira na tabela 'transacoes'.

    Armazena os detalhes de uma receita ou despesa, vinculada a um usuário
    e a uma categoria.

    Attributes:
        id (int): Identificador único da transação (Chave Primária).
        descricao (str): Descrição ou título da transação.
        valor (Decimal): Valor monetário da transação.
        data (datetime): Data e hora da ocorrência da transação.
        observacoes (Optional[str]): Notas adicionais sobre a transação.
        categoria_id (int): ID da categoria associada (Chave Estrangeira).
        usuario_id (int): ID do usuário proprietário (Chave Estrangeira).
        categoria (Categoria): Objeto da categoria associada.
        proprietario (Usuario): Objeto do usuário proprietário.
    """
    __tablename__ = "transacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Decisão de Engenharia: Numeric para precisão financeira
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    data: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Chaves Estrangeiras
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)

    # Relacionamentos
    categoria: Mapped["Categoria"] = relationship(
        back_populates="transacoes"
    )
    
    proprietario: Mapped["Usuario"] = relationship(
        back_populates="transacoes"
    )
