from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import decimal
from . import models, schemas, security

# --- USUÁRIO ---
def get_usuario_por_nome(db: Session, nome_usuario: str):
    return db.query(models.Usuario).filter(models.Usuario.nome_usuario == nome_usuario).first()

def criar_usuario(db: Session, usuario: schemas.UsuarioCreate):
    hash_da_senha = security.get_hash_da_senha(usuario.senha)
    db_usuario = models.Usuario(nome_usuario=usuario.nome_usuario, senha_hash=hash_da_senha)
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

# --- CATEGORIA (LÓGICA GLOBAL) ---

# <-- CORRIGIDO: Não recebe mais 'usuario_id'
def criar_categoria(db: Session, categoria: schemas.CategoriaCreate):
    """Cria uma nova categoria GLOBAIL no banco de dados."""
    db_categoria = models.Categoria(**categoria.model_dump())
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

# <-- CORRIGIDO: Função preenchida e sem filtro de usuário
def listar_categorias(db: Session):
    """Retorna uma lista de TODAS as categorias GLOBAIS."""
    # .all() sempre retorna uma lista (ex: []), o que corrige o erro
    return db.query(models.Categoria).all()


# --- TRANSAÇÃO ---
def criar_transacao(db: Session, transacao: schemas.TransacaoCreate, usuario_id: int):
    db_transacao = models.Transacao(**transacao.model_dump(), usuario_id=usuario_id)
    db.add(db_transacao)
    db.commit()
    db.refresh(db_transacao)
    return db_transacao

def listar_transacoes(db: Session, usuario_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Transacao).filter(
        models.Transacao.usuario_id == usuario_id
    ).order_by(
        models.Transacao.data.desc()
    ).offset(skip).limit(limit).all()

# --- DASHBOARD ---
def get_dashboard_data(db: Session, usuario_id: int, data_inicio: date, data_fim: date):
    total_receitas = db.query(func.sum(models.Transacao.valor)).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Receita",
        models.Transacao.data.between(data_inicio, data_fim)
    ).scalar() or decimal.Decimal(0)

    total_gastos = db.query(func.sum(models.Transacao.valor)).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Gasto",
        models.Transacao.data.between(data_inicio, data_fim)
    ).scalar() or decimal.Decimal(0)

    lucro_liquido = total_receitas - total_gastos

    gastos_por_categoria_query = db.query(
        models.Categoria.nome,
        func.sum(models.Transacao.valor).label("valor_total")
    ).join(models.Transacao).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Gasto",
        models.Transacao.data.between(data_inicio, data_fim)
    ).group_by(models.Categoria.nome).order_by(
        func.sum(models.Transacao.valor).desc()
    ).all()

    gastos_por_categoria = [
        schemas.GastoPorCategoria(nome_categoria=nome, valor_total=total)
        for nome, total in gastos_por_categoria_query
    ]

    return schemas.DashboardData(
        total_receitas=total_receitas,
        total_gastos=total_gastos,
        lucro_liquido=lucro_liquido,
        gastos_por_categoria=gastos_por_categoria
    )