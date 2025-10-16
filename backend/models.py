# Arquivo: backend/models.py
# Responsabilidade: Definir as classes Python (Modelos) que representam as tabelas no nosso banco de dados.

# Importa as ferramentas necessárias do SQLAlchemy para definir colunas e relacionamentos.
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

# Importa a classe 'Base' que criamos no arquivo database.py.
# Todas as nossas classes de modelo herdarão desta Base.
from .database import Base


# --- MODELO DA TABELA DE USUÁRIOS ---
class Usuario(Base):
    # __tablename__ é o nome oficial da tabela no banco de dados.
    __tablename__ = "usuarios"

    # Definição das colunas da tabela "usuarios".
    id = Column(Integer, primary_key=True, index=True)
    nome_usuario = Column(String(100), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    # Definição do relacionamento com a tabela de Transacao.
    # 'transacoes' será um atributo no objeto Usuario que conterá uma lista de todas as suas transações.
    # 'back_populates' cria o link reverso no modelo Transacao, no atributo 'proprietario'.
    transacoes = relationship("Transacao", back_populates="proprietario")


# --- MODELO DA TABELA DE CATEGORIAS ---
class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, index=True, nullable=False)
    tipo = Column(String(50), nullable=False, comment="Define se é 'Gasto' ou 'Receita'")

    transacoes = relationship("Transacao", back_populates="categoria")


# --- MODELO DA TABELA DE TRANSAÇÕES ---
class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String(255), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)  # Ex: 12345678.99
    data = Column(DateTime, nullable=False, default=datetime.utcnow)
    observacoes = Column(String(500), nullable=True) # O campo que você adicionou!

    # Definição das Chaves Estrangeiras (os links físicos entre as tabelas).
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    # Definição dos relacionamentos a nível de objeto.
    # Agora, a partir de um objeto Transacao, podemos acessar o objeto Categoria inteiro
    # através do atributo `transacao.categoria`.
    categoria = relationship("Categoria", back_populates="transacoes")
    proprietario = relationship("Usuario", back_populates="transacoes")