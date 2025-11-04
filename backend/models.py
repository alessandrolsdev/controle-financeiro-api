# Arquivo: backend/models.py
# Responsabilidade: Definir a ESTRUTURA das tabelas no banco de dados.
# Esta é a camada "Model" da nossa arquitetura.
#
# Utilizamos a sintaxe moderna do SQLAlchemy 2.0 (com Mapped e mapped_column)
# para garantir "tipagem" (type-hinting) completa no nosso código.

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

# Importa a Base declarativa que criamos no arquivo database.py
from .database import Base


# --- 1. MODELO DA TABELA DE USUÁRIOS ---
class Usuario(Base):
    """
    Representa um usuário no sistema.
    Este é o "dono" das transações financeiras.
    """
    __tablename__ = "usuarios"

    # Coluna Primária
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Informações de Autenticação
    nome_usuario: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Metadados
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relacionamento Reverso: Um usuário pode ter muitas transações.
    # O 'lazy="selectin"' é uma otimização de performance moderna.
    transacoes: Mapped[List["Transacao"]] = relationship(
        back_populates="proprietario", lazy="selectin"
    )


# --- 2. MODELO DA TABELA DE CATEGORIAS ---
class Categoria(Base):
    """
    Representa uma categoria para classificar transações (ex: "Combustível", "Alimentação").
    Nesta versão, as categorias são globais (compartilhadas por todos os usuários).
    """
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    
    # Define se a categoria é uma "Gasto" (Despesa) ou "Receita" (Ganho)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relacionamento Reverso: Uma categoria pode estar em muitas transações.
    transacoes: Mapped[List["Transacao"]] = relationship(
        back_populates="categoria", lazy="selectin"
    )


# --- 3. MODELO DA TABELA DE TRANSAÇÕES (O CORAÇÃO DO SISTEMA) ---
class Transacao(Base):
    """
    Representa um único registro financeiro (um gasto ou um ganho).
    Cada transação pertence a um Usuário e a uma Categoria.
    """
    __tablename__ = "transacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Usamos Numeric/Decimal para valores financeiros, garantindo precisão.
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Data em que a transação ocorreu (definida pelo usuário).
    data: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Campo opcional para notas extras (ex: placa do trator, local).
    # Usamos 'Text' em vez de 'String(500)' para anotações mais longas.
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Chaves Estrangeiras (os links físicos entre as tabelas)
    
    # FOREIGN KEY para a tabela Categoria
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"), nullable=False)
    
    # FOREIGN KEY para a tabela Usuario (quem fez o registro)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)

    # Relacionamentos (os "atalhos" do Python para acessar os objetos)
    
    # Permite acessar o objeto Categoria completo via 'minha_transacao.categoria'
    categoria: Mapped["Categoria"] = relationship(
        back_populates="transacoes", lazy="joined"
    )
    
    # Permite acessar o objeto Usuario completo via 'minha_transacao.proprietario'
    proprietario: Mapped["Usuario"] = relationship(
        back_populates="transacoes", lazy="joined"
    )