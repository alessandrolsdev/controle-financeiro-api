# Arquivo: backend/crud.py (VERSÃO FINAL COM DOCSTRINGS)

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
import decimal

from . import models, schemas, security

# --- 1. FUNÇÕES CRUD PARA USUÁRIO ---

def get_usuario_por_nome(db: Session, nome_usuario: str) -> models.Usuario | None:
    """
    Busca um usuário no banco de dados pelo nome de usuário.

    Args:
        db (Session): A sessão do banco de dados.
        nome_usuario (str): O nome de usuário a ser buscado.

    Returns:
        models.Usuario | None: O objeto do usuário se encontrado, senão None.
    """
    return db.query(models.Usuario).filter(models.Usuario.nome_usuario == nome_usuario).first()

def criar_usuario(db: Session, usuario: schemas.UsuarioCreate) -> models.Usuario:
    """
    Cria um novo usuário no banco de dados com uma senha hasheada.

    Args:
        db (Session): A sessão do banco de dados.
        usuario (schemas.UsuarioCreate): Os dados do novo usuário (com senha em texto plano).

    Returns:
        models.Usuario: O objeto do usuário recém-criado.
    """
    # Usa o cofre de segurança para gerar o hash seguro
    hash_da_senha = security.get_hash_da_senha(usuario.senha)
    
    # Cria a instância do modelo SQLAlchemy, trocando a senha pelo hash
    db_usuario = models.Usuario(nome_usuario=usuario.nome_usuario, senha_hash=hash_da_senha)
    
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario


# --- 2. FUNÇÕES CRUD PARA CATEGORIA ---

def criar_categoria(db: Session, categoria: schemas.CategoriaCreate) -> models.Categoria:
    """
    Cria uma nova categoria no banco de dados.

    Args:
        db (Session): A sessão do banco de dados.
        categoria (schemas.CategoriaCreate): Os dados da nova categoria.

    Returns:
        models.Categoria: O objeto da categoria recém-criada.
    """
    db_categoria = models.Categoria(**categoria.model_dump())
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

def listar_categorias(db: Session) -> list[models.Categoria]:
    """
    Retorna uma lista de todas as categorias do banco de dados.
    (Nota: Categorias são globais, não por usuário, nesta versão).

    Args:
        db (Session): A sessão do banco de dados.

    Returns:
        list[models.Categoria]: Uma lista de todos os objetos de categoria.
    """
    return db.query(models.Categoria).all()


# --- 3. FUNÇÕES CRUD PARA TRANSAÇÃO ---

def criar_transacao(db: Session, transacao: schemas.TransacaoCreate, usuario_id: int) -> models.Transacao:
    """
    Cria uma nova transação (gasto ou receita) no banco, associada a um usuário.

    Args:
        db (Session): A sessão do banco de dados.
        transacao (schemas.TransacaoCreate): Os dados da nova transação (com 'data').
        usuario_id (int): O ID do usuário que está registrando a transação.

    Returns:
        models.Transacao: O objeto da transação recém-criada.
    """
    db_transacao = models.Transacao(**transacao.model_dump(), usuario_id=usuario_id)
    db.add(db_transacao)
    db.commit()
    db.refresh(db_transacao)
    return db_transacao

def listar_transacoes(db: Session, usuario_id: int, skip: int = 0, limit: int = 100) -> list[models.Transacao]:
    """
    Retorna uma lista de transações com paginação, filtrada por usuário.

    Args:
        db (Session): A sessão do banco de dados.
        usuario_id (int): O ID do usuário para filtrar as transações.
        skip (int): O número de registros a pular (para paginação).
        limit (int): O número máximo de registros a retornar (para paginação).

    Returns:
        list[models.Transacao]: Uma lista de transações do usuário.
    """
    return db.query(models.Transacao).filter(
        models.Transacao.usuario_id == usuario_id
    ).order_by(
        models.Transacao.data.desc() # Ordena pelas mais recentes
    ).offset(skip).limit(limit).all()


# --- 4. FUNÇÃO DE LÓGICA DE NEGÓCIOS (Dashboard) ---

def get_dashboard_data(db: Session, usuario_id: int, data_inicio: date, data_fim: date) -> schemas.DashboardData:
    """
    Busca e calcula os dados de resumo financeiro para o dashboard de um usuário
    específico, dentro de um intervalo de datas.

    Args:
        db (Session): A sessão do banco de dados.
        usuario_id (int): O ID do usuário para filtrar os dados.
        data_inicio (date): A data inicial do período (inclusivo).
        data_fim (date): A data final do período (inclusivo).

    Returns:
        schemas.DashboardData: Um objeto Pydantic com todos os totais calculados.
    """
    
    # --- Correção do Bug de "Fim do Dia" ---
    # Adicionamos 1 dia ao 'data_fim' para que a consulta
    # procure por datas < (menor que) 00:00 do dia seguinte.
    data_fim_query = data_fim + timedelta(days=1)
    
    # 1. Calcula o Total de Receitas
    total_receitas = db.query(func.sum(models.Transacao.valor)).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Receita",
        models.Transacao.data >= data_inicio,
        models.Transacao.data < data_fim_query
    ).scalar() or decimal.Decimal(0)

    # 2. Calcula o Total de Gastos
    total_gastos = db.query(func.sum(models.Transacao.valor)).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Gasto",
        models.Transacao.data >= data_inicio,
        models.Transacao.data < data_fim_query
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
        models.Transacao.data >= data_inicio,
        models.Transacao.data < data_fim_query
    ).group_by(models.Categoria.nome).order_by(
        func.sum(models.Transacao.valor).desc()
    ).all()

    # 5. Formata os resultados da query em objetos Pydantic
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