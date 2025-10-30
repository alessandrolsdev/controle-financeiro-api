# Arquivo: backend/crud.py (versão atualizada)

from sqlalchemy.orm import Session
from sqlalchemy import func  
from . import models, schemas, security
from datetime import date  
import decimal  

# --- ADICIONADO AGORA: Lógica do Dashboard ---

def get_dashboard_data(db: Session, usuario_id: int, data_inicio: date, data_fim: date):
    """
    Busca e calcula os dados de resumo financeiro para o dashboard.
    """
    
    # 1. Calcula o Total de Receitas
    total_receitas = db.query(func.sum(models.Transacao.valor)).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Receita",
        models.Transacao.data.between(data_inicio, data_fim)
    ).scalar() or decimal.Decimal(0) # 'scalar()' pega o primeiro valor, 'or 0' trata se for Nulo

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
        func.sum(models.Transacao.valor).label("valor_total") # 'label' dá um nome ao resultado da soma
    ).join(models.Transacao).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Gasto",
        models.Transacao.data.between(data_inicio, data_fim)
    ).group_by(models.Categoria.nome).order_by(
        func.sum(models.Transacao.valor).desc() # Ordena do maior gasto para o menor
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