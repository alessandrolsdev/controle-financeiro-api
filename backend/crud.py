# Arquivo: backend/crud.py (VERSÃO COMPLETA V7.0)
"""
CHECK-UP (V7.0): Adiciona as funções
'atualizar_detalhes_usuario' e 'mudar_senha_usuario'.
"""

# --- 1. Importações ---
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, cast, Date 
from datetime import date, timedelta
import decimal

from . import models, schemas, security

# --- 2. FUNÇÕES CRUD (USUÁRIO) ---
def get_usuario_por_nome(db: Session, nome_usuario: str) -> models.Usuario | None:
    return db.query(models.Usuario).filter(models.Usuario.nome_usuario == nome_usuario).first()

def criar_usuario(db: Session, usuario: schemas.UsuarioCreate) -> models.Usuario:
    hash_da_senha = security.get_hash_da_senha(usuario.senha)
    db_usuario = models.Usuario(nome_usuario=usuario.nome_usuario, senha_hash=hash_da_senha)
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

# --- NOVAS FUNÇÕES (V7.0) ---
def atualizar_detalhes_usuario(
    db: Session, 
    usuario: models.Usuario, 
    detalhes: schemas.UsuarioUpdate
) -> models.Usuario:
    """Atualiza os campos de perfil (não-sensíveis) de um usuário."""
    # Pega os dados do schema Pydantic
    update_data = detalhes.model_dump(exclude_unset=True)
    
    # Atualiza o objeto do SQLAlchemy
    for key, value in update_data.items():
        setattr(usuario, key, value)
        
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario

def mudar_senha_usuario(
    db: Session, 
    usuario: models.Usuario, 
    payload: schemas.UsuarioChangePassword
) -> bool:
    """
    Verifica a senha antiga e, se correta, atualiza para a nova senha.
    Retorna True se foi bem-sucedido, False se a senha antiga
    estiver incorreta.
    """
    # 1. Verifica a senha antiga (CRÍTICO)
    if not security.verificar_senha(payload.senha_antiga, usuario.senha_hash):
        return False # Senha antiga não confere
    
    # 2. Gera o hash da nova senha
    novo_hash = security.get_hash_da_senha(payload.senha_nova)
    
    # 3. Salva a nova senha
    usuario.senha_hash = novo_hash
    db.add(usuario)
    db.commit()
    
    return True
# ----------------------------

# --- 3. FUNÇÕES CRUD (CATEGORIA) ---
# ... (criar_categoria, listar_categorias) ...
def criar_categoria(db: Session, categoria: schemas.CategoriaCreate) -> models.Categoria:
    db_categoria = models.Categoria(**categoria.model_dump())
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

def listar_categorias(db: Session) -> list[models.Categoria]:
    return db.query(models.Categoria).all()

# --- 4. FUNÇÕES CRUD (TRANSAÇÃO) ---
# ... (criar_transacao, atualizar_transacao, listar_transacoes, listar_transacoes_por_periodo) ...
def criar_transacao(db: Session, transacao: schemas.TransacaoCreate, usuario_id: int) -> models.Transacao:
    db_transacao = models.Transacao(**transacao.model_dump(), usuario_id=usuario_id)
    db.add(db_transacao)
    db.commit()
    db.refresh(db_transacao)
    return db_transacao

def atualizar_transacao(
    db: Session, 
    transacao_id: int, 
    transacao: schemas.TransacaoCreate,
    usuario_id: int
) -> models.Transacao | None:
    db_transacao = db.query(models.Transacao).filter(
        models.Transacao.id == transacao_id
    ).first()
    if db_transacao is None:
        return None
    if db_transacao.usuario_id != usuario_id:
        return None
    update_data = transacao.model_dump()
    db_transacao.descricao = update_data['descricao']
    db_transacao.valor = update_data['valor']
    db_transacao.categoria_id = update_data['categoria_id']
    db_transacao.data = update_data['data']
    db_transacao.observacoes = update_data['observacoes']
    db.add(db_transacao)
    db.commit()
    db.refresh(db_transacao)
    return db_transacao

def listar_transacoes(db: Session, usuario_id: int, skip: int = 0, limit: int = 100) -> list[models.Transacao]:
    return db.query(models.Transacao).options(
        joinedload(models.Transacao.categoria)
    ).filter(
        models.Transacao.usuario_id == usuario_id
    ).order_by(
        models.Transacao.data.desc()
    ).offset(skip).limit(limit).all()

def listar_transacoes_por_periodo(
    db: Session, 
    usuario_id: int, 
    data_inicio: date, 
    data_fim: date
) -> list[models.Transacao]:
    data_fim_query = data_fim + timedelta(days=1)
    return db.query(models.Transacao).options(
        joinedload(models.Transacao.categoria)
    ).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Transacao.data >= data_inicio,
        models.Transacao.data < data_fim_query
    ).order_by(
        models.Transacao.data.desc() 
    ).all()


# --- 5. FUNÇÃO DO DASHBOARD ---
def get_dashboard_data(db: Session, usuario_id: int, data_inicio: date, data_fim: date) -> schemas.DashboardData:
    data_fim_query = data_fim + timedelta(days=1)
    total_receitas = db.query(func.sum(models.Transacao.valor)).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Receita",
        models.Transacao.data >= data_inicio,
        models.Transacao.data < data_fim_query
    ).scalar() or decimal.Decimal(0)
    total_gastos = db.query(func.sum(models.Transacao.valor)).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Gasto",
        models.Transacao.data >= data_inicio,
        models.Transacao.data < data_fim_query
    ).scalar() or decimal.Decimal(0)
    lucro_liquido = total_receitas - total_gastos
    gastos_por_categoria_query = db.query(
        models.Categoria.nome,
        models.Categoria.cor,
        func.sum(models.Transacao.valor).label("valor_total"),
        func.count(models.Transacao.id).label("total_compras")
    ).join(models.Transacao).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Gasto",
        models.Transacao.data >= data_inicio,
        models.Transacao.data < data_fim_query
    ).group_by(models.Categoria.nome, models.Categoria.cor).order_by(
        func.sum(models.Transacao.valor).desc()
    ).all()
    receitas_por_categoria_query = db.query(
        models.Categoria.nome,
        models.Categoria.cor,
        func.sum(models.Transacao.valor).label("valor_total"),
        func.count(models.Transacao.id).label("total_compras")
    ).join(models.Transacao).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Receita",
        models.Transacao.data >= data_inicio,
        models.Transacao.data < data_fim_query
    ).group_by(models.Categoria.nome, models.Categoria.cor).order_by(
        func.sum(models.Transacao.valor).desc()
    ).all()
    gastos_por_categoria = [
        schemas.CategoriaDetalhada(
            nome_categoria=nome, 
            cor=cor,
            valor_total=total, 
            total_compras=count
        )
        for nome, cor, total, count in gastos_por_categoria_query
    ]
    receitas_por_categoria = [
        schemas.CategoriaDetalhada(
            nome_categoria=nome, 
            cor=cor,
            valor_total=total, 
            total_compras=count
        )
        for nome, cor, total, count in receitas_por_categoria_query
    ]
    return schemas.DashboardData(
        total_receitas=total_receitas,
        total_gastos=total_gastos,
        lucro_liquido=lucro_liquido,
        gastos_por_categoria=gastos_por_categoria,
        receitas_por_categoria=receitas_por_categoria
    )
    
# --- 6. FUNÇÃO DE RELATÓRIOS ---
def get_dados_de_tendencia(
    db: Session, 
    usuario_id: int, 
    data_inicio: date, 
    data_fim: date,
    filtro: str
) -> schemas.DadosDeTendencia:
    
    data_fim_query = data_fim + timedelta(days=1)
    if filtro == 'daily':
        agrupador_de_data = func.strftime('%Y-%m-%d %H:00:00', models.Transacao.data)
        ordenador_de_data = func.strftime('%Y-%m-%d %H:00:00', models.Transacao.data)
    else:
        agrupador_de_data = func.date(models.Transacao.data)
        ordenador_de_data = func.date(models.Transacao.data)
    query_receitas = db.query(
        agrupador_de_data.label("data"),
        func.sum(models.Transacao.valor).label("valor")
    ).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Receita",
        models.Transacao.data >= data_inicio,
        models.Transacao.data < data_fim_query
    ).group_by(
        agrupador_de_data
    ).order_by(
        ordenador_de_data
    ).all()
    query_despesas = db.query(
        agrupador_de_data.label("data"),
        func.sum(models.Transacao.valor).label("valor")
    ).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Gasto",
        models.Transacao.data >= data_inicio,
        models.Transacao.data < data_fim_query
    ).group_by(
        agrupador_de_data
    ).order_by(
        ordenador_de_data
    ).all()
    receitas = [schemas.PontoDeTendencia(data=r.data, valor=r.valor) for r in query_receitas]
    despesas = [schemas.PontoDeTendencia(data=d.data, valor=d.valor) for d in query_despesas]
    return schemas.DadosDeTendencia(receitas=receitas, despesas=despesas)