# Arquivo: backend/crud.py (VERSÃO FINAL COM CORREÇÃO DE FUSO HORÁRIO)

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta # <-- Importação necessária
import decimal

# Importa nossos módulos de Modelos, Schemas e Segurança
from . import models, schemas, security

# --- 1. FUNÇÕES CRUD PARA USUÁRIO ---

def get_usuario_por_nome(db: Session, nome_usuario: str):
    """Busca e retorna um usuário pelo seu nome de usuário."""
    return db.query(models.Usuario).filter(models.Usuario.nome_usuario == nome_usuario).first()

def criar_usuario(db: Session, usuario: schemas.UsuarioCreate):
    """Cria um novo usuário, com a senha "hashed"."""
    hash_da_senha = security.get_hash_da_senha(usuario.senha)
    db_usuario = models.Usuario(nome_usuario=usuario.nome_usuario, senha_hash=hash_da_senha)
    
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario


# --- 2. FUNÇÕES CRUD PARA CATEGORIA ---

def criar_categoria(db: Session, categoria: schemas.CategoriaCreate):
    """Cria uma nova categoria no banco de dados."""
    db_categoria = models.Categoria(**categoria.model_dump())
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

def listar_categorias(db: Session):
    """Retorna uma lista de todas as categorias do banco de dados."""
    # Categorias são globais, então listamos todas
    return db.query(models.Categoria).all()


# --- 3. FUNÇÕES CRUD PARA TRANSAÇÃO ---

def criar_transacao(db: Session, transacao: schemas.TransacaoCreate, usuario_id: int):
    """Cria uma nova transação (gasto ou receita) no banco."""
    db_transacao = models.Transacao(**transacao.model_dump(), usuario_id=usuario_id)
    db.add(db_transacao)
    db.commit()
    db.refresh(db_transacao)
    return db_transacao

def listar_transacoes(db: Session, usuario_id: int, skip: int = 0, limit: int = 100):
    """Retorna uma lista de transações com paginação, APENAS para o usuário especificado."""
    # Versão segura: filtra por usuário E ordena por data
    return db.query(models.Transacao).filter(
        models.Transacao.usuario_id == usuario_id
    ).order_by(
        models.Transacao.data.desc() # Mostra os mais recentes primeiro
    ).offset(skip).limit(limit).all()


# --- 4. FUNÇÃO DE LÓGICA DE NEGÓCIOS (Dashboard) ---

def get_dashboard_data(db: Session, usuario_id: int, data_inicio: date, data_fim: date):
    """
    Busca e calcula os dados de resumo financeiro para o dashboard.
    """
    
    # --- A CORREÇÃO DO BUG DE FIM DO DIA ---
    # Adicionamos 1 dia ao 'data_fim' para garantir que pegamos
    # todas as transações feitas *durante* o último dia.
    # A consulta agora procura por datas < (menor que) o início do dia seguinte.
    data_fim_query = data_fim + timedelta(days=1)
    
    # 1. Calcula o Total de Receitas
    total_receitas = db.query(func.sum(models.Transacao.valor)).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Receita",
        models.Transacao.data >= data_inicio,     # >= data de início
        models.Transacao.data < data_fim_query    # < data final (corrigido)
    ).scalar() or decimal.Decimal(0)

    # 2. Calcula o Total de Gastos
    total_gastos = db.query(func.sum(models.Transacao.valor)).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Gasto",
        models.Transacao.data >= data_inicio,     # >= data de início
        models.Transacao.data < data_fim_query    # < data final (corrigido)
    ).scalar() or decimal.Decimal(0)

    # 3. Calcula o Lucro Líquido
    lucro_liquido = total_receitas - total_gastos

    # 4. Busca o total de gastos agrupado por categoria
    gastos_por_categoria_query = db.query(
        models.Categoria.nome,
        func.sum(models.Transacao.valor).label("valor_total")
    ).join(models.Transacao).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Gasto",
        models.Transacao.data >= data_inicio,     # >= data de início
        models.Transacao.data < data_fim_query    # < data final (corrigido)
    ).group_by(models.Categoria.nome).order_by(
        func.sum(models.Transacao.valor).desc()
    ).all()

    # 5. Formata os resultados da query em objetos do nosso schema
    gastos_por_categoria = [
        schemas.GastoPorCategoria(nome_categoria=nome, valor_total=total)
        for nome, total in gastos_por_categoria_query
    ]

    # 6. Retorna o objeto de dados completo do dashboard
    return schemas.DashboardData(
        total_receitas=total_receitas,
        total_gastos=total_gastos,
        lucro_liquido=lucro_liquido,
        gastos_por_categoria=gastos_por_categoria
    )