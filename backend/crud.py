# Arquivo: backend/crud.py
# Responsabilidade: Conter as funções que interagem diretamente com o banco de dados (CRUD).

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import decimal

# Importa nossos módulos de Modelos, Schemas e Segurança
from . import models, schemas, security

# --- 1. FUNÇÕES CRUD PARA USUÁRIO ---

def get_usuario_por_nome(db: Session, nome_usuario: str):
    """Busca e retorna um usuário pelo seu nome de usuário."""
    return db.query(models.Usuario).filter(models.Usuario.nome_usuario == nome_usuario).first()

def criar_usuario(db: Session, usuario: schemas.UsuarioCreate):
    """Cria um novo usuário, com a senha "hashed"."""
    # Pega a senha em texto plano e usa nosso cofre para gerar o hash
    hash_da_senha = security.get_hash_da_senha(usuario.senha)
    # Cria o objeto do modelo, trocando a senha pelo hash
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

def listar_categorias(db: Session, usuario_id: int):
    """Retorna uma lista de categorias APENAS para o usuário especificado."""
    # Nota: Isso assume que você quer que categorias sejam por usuário.
    # Se categorias forem GLOBAIS (todos usuários veem as mesmas),
    # podemos deixar como estava. Mas para um controle financeiro,
    # é melhor que cada usuário tenha suas próprias categorias.
    # Para isso, precisamos adicionar 'usuario_id' ao 'models.Categoria'.


# --- 3. FUNÇÕES CRUD PARA TRANSAÇÃO ---

def criar_transacao(db: Session, transacao: schemas.TransacaoCreate, usuario_id: int):
    """Cria uma nova transação (gasto ou receita) no banco."""
    # Usa o .model_dump() do Pydantic para desempacotar os dados
    db_transacao = models.Transacao(**transacao.model_dump(), usuario_id=usuario_id)
    db.add(db_transacao)
    db.commit()
    db.refresh(db_transacao)
    return db_transacao

def listar_transacoes(db: Session, usuario_id: int, skip: int = 0, limit: int = 100):
    """Retorna uma lista de transações com paginação, APENAS para o usuário especificado."""
    return db.query(models.Transacao).filter(
        models.Transacao.usuario_id == usuario_id
    ).order_by(
        models.Transacao.data.desc() # Bônus: mostra os gastos mais recentes primeiro
    ).offset(skip).limit(limit).all()


# --- 4. FUNÇÃO DE LÓGICA DE NEGÓCIOS (Dashboard) ---

def get_dashboard_data(db: Session, usuario_id: int, data_inicio: date, data_fim: date):
    """
    Busca e calcula os dados de resumo financeiro para o dashboard.
    """
    
    # 1. Calcula o Total de Receitas
    total_receitas = db.query(func.sum(models.Transacao.valor)).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Receita",
        models.Transacao.data.between(data_inicio, data_fim)
    ).scalar() or decimal.Decimal(0)

    # 2. Calcula o Total de Gastos
    total_gastos = db.query(func.sum(models.Transacao.valor)).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Gasto",
        models.Transacao.data.between(data_inicio, data_fim)
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
        models.Transacao.data.between(data_inicio, data_fim)
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