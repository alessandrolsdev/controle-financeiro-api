# Arquivo: backend/crud.py (versão atualizada)

from sqlalchemy.orm import Session
from . import models, schemas
from . import security
# --- Funções CRUD para Usuário ---

def get_usuario_por_nome(db: Session, nome_usuario: str):
    """Busca e retorna um usuário pelo seu nome de usuário."""
    return db.query(models.Usuario).filter(models.Usuario.nome_usuario == nome_usuario).first()

def criar_usuario(db: Session, usuario: schemas.UsuarioCreate):
    """Cria um novo usuário, com a senha "hashed"."""
    # Pega a senha em texto plano e gera o hash seguro
    hash_da_senha = security.get_hash_da_senha(usuario.senha)
    # Cria o objeto do modelo, mas trocando a senha pelo hash
    db_usuario = models.Usuario(nome_usuario=usuario.nome_usuario, senha_hash=hash_da_senha)
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

# --- Funções CRUD para Categoria ---

def criar_categoria(db: Session, categoria: schemas.CategoriaCreate):
    """Cria uma nova categoria no banco de dados."""
    db_categoria = models.Categoria(**categoria.model_dump())
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

def listar_categorias(db: Session):
    """Retorna uma lista de todas as categorias do banco de dados."""
    return db.query(models.Categoria).all()


# --- Função CRUD para Transação (já existente) ---

def criar_transacao(db: Session, transacao: schemas.TransacaoCreate, usuario_id: int):
    """Cria uma nova transação no banco de dados."""
    db_transacao = models.Transacao(**transacao.model_dump(), usuario_id=usuario_id)
    db.add(db_transacao)
    db.commit()
    db.refresh(db_transacao)
    return db_transacao

def listar_transacoes(db: Session, skip: int = 0, limit: int = 100):
    """
    Retorna uma lista de transações do banco de dados, com paginação.
    - skip: o número de registros a pular.
    - limit: o número máximo de registros a retornar.
    """
    return db.query(models.Transacao).offset(skip).limit(limit).all()