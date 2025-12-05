# Arquivo: backend/crud.py
"""Módulo de Operações CRUD (Create, Read, Update, Delete).

Este módulo contém toda a lógica de interação com o banco de dados. Ele serve
como uma camada de abstração entre os endpoints da API e os modelos de dados.

Inclui operações para gerenciamento de usuários, categorias, transações e
geração de dados analíticos para dashboards.

Functions:
    get_usuario_por_nome: Busca um usuário pelo nome de usuário.
    criar_usuario: Cria um novo usuário no sistema.
    atualizar_detalhes_usuario: Atualiza dados do perfil do usuário.
    mudar_senha_usuario: Altera a senha do usuário.
    criar_categoria: Cria uma nova categoria de transação.
    listar_categorias: Retorna todas as categorias cadastradas.
    atualizar_categoria: Atualiza uma categoria existente.
    deletar_categoria: Remove uma categoria do sistema.
    criar_transacao: Registra uma nova transação financeira.
    atualizar_transacao: Modifica uma transação existente.
    deletar_transacao: Remove uma transação.
    listar_transacoes: Lista transações com paginação.
    listar_transacoes_por_periodo: Lista transações em um intervalo de datas.
    get_dashboard_data: Calcula métricas financeiras consolidadas.
    get_dados_de_tendencia: Gera dados para gráficos de evolução financeira.
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, cast, Date 
from sqlalchemy.exc import IntegrityError 
from datetime import date, timedelta
import decimal

from . import models, schemas, security

# --- FUNÇÕES CRUD (USUÁRIO) ---

def get_usuario_por_nome(db: Session, nome_usuario: str) -> models.Usuario | None:
    """Busca um registro de usuário pelo nome de usuário (username).

    Args:
        db (Session): Sessão ativa do banco de dados.
        nome_usuario (str): O nome de usuário a ser pesquisado.

    Returns:
        models.Usuario | None: O objeto usuário se encontrado, caso contrário None.
    """
    return db.query(models.Usuario).filter(models.Usuario.nome_usuario == nome_usuario).first()

def criar_usuario(db: Session, usuario: schemas.UsuarioCreate) -> models.Usuario:
    """Registra um novo usuário no banco de dados.

    Realiza o hash da senha antes de salvar.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario (schemas.UsuarioCreate): Dados do usuário para criação.

    Returns:
        models.Usuario: O objeto usuário recém-criado.
    """
    hash_da_senha = security.get_hash_da_senha(usuario.senha)
    
    db_usuario = models.Usuario(nome_usuario=usuario.nome_usuario, senha_hash=hash_da_senha)
    
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def atualizar_detalhes_usuario(
    db: Session, 
    usuario: models.Usuario, 
    detalhes: schemas.UsuarioUpdate
) -> models.Usuario:
    """Atualiza as informações de perfil de um usuário existente.

    Apenas os campos fornecidos no objeto `detalhes` serão atualizados.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario (models.Usuario): Instância do usuário a ser atualizada.
        detalhes (schemas.UsuarioUpdate): Novos dados para atualização.

    Returns:
        models.Usuario: O objeto usuário atualizado.
    """
    update_data = detalhes.model_dump(exclude_unset=True)
    
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
    """Altera a senha de acesso do usuário.

    Verifica se a senha antiga fornecida corresponde ao hash armazenado antes
    de aplicar a nova senha.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario (models.Usuario): O usuário que está alterando a senha.
        payload (schemas.UsuarioChangePassword): Objeto contendo a senha antiga e a nova.

    Returns:
        bool: True se a senha foi alterada com sucesso, False se a senha antiga estiver incorreta.
    """
    if not security.verificar_senha(payload.senha_antiga, usuario.senha_hash):
        return False
    
    novo_hash = security.get_hash_da_senha(payload.senha_nova)
    
    usuario.senha_hash = novo_hash
    db.add(usuario)
    db.commit()
    
    return True

# --- FUNÇÕES CRUD (CATEGORIA) ---

def criar_categoria(db: Session, categoria: schemas.CategoriaCreate) -> models.Categoria:
    """Adiciona uma nova categoria de transação ao sistema.

    Args:
        db (Session): Sessão ativa do banco de dados.
        categoria (schemas.CategoriaCreate): Dados da categoria a ser criada.

    Returns:
        models.Categoria: O objeto categoria criado.
    """
    db_categoria = models.Categoria(**categoria.model_dump())
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

def listar_categorias(db: Session) -> list[models.Categoria]:
    """Retorna a lista de todas as categorias disponíveis.

    Args:
        db (Session): Sessão ativa do banco de dados.

    Returns:
        list[models.Categoria]: Lista de objetos de categoria.
    """
    return db.query(models.Categoria).all()

def atualizar_categoria(
    db: Session, 
    categoria_id: int, 
    categoria_update: schemas.CategoriaUpdate
) -> models.Categoria | None:
    """Atualiza os dados de uma categoria específica.

    Args:
        db (Session): Sessão ativa do banco de dados.
        categoria_id (int): ID da categoria a ser atualizada.
        categoria_update (schemas.CategoriaUpdate): Dados para atualização.

    Returns:
        models.Categoria | None: A categoria atualizada ou None se não encontrada.
    """
    db_categoria = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
    if not db_categoria:
        return None
        
    update_data = categoria_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_categoria, key, value)
        
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

def deletar_categoria(db: Session, categoria_id: int) -> bool:
    """Remove uma categoria do banco de dados.

    Args:
        db (Session): Sessão ativa do banco de dados.
        categoria_id (int): ID da categoria a ser removida.

    Returns:
        bool: True se a categoria foi removida, False se não encontrada.
    """
    db_categoria = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
    if not db_categoria:
        return False
    
    db.delete(db_categoria)
    db.commit()
    return True

# --- FUNÇÕES CRUD (TRANSAÇÃO) ---

def criar_transacao(db: Session, transacao: schemas.TransacaoCreate, usuario_id: int) -> models.Transacao:
    """Registra uma nova transação financeira para um usuário.

    Args:
        db (Session): Sessão ativa do banco de dados.
        transacao (schemas.TransacaoCreate): Dados da transação.
        usuario_id (int): ID do usuário proprietário da transação.

    Returns:
        models.Transacao: A transação criada.
    """
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
    """Atualiza uma transação existente, garantindo a propriedade do usuário.

    Args:
        db (Session): Sessão ativa do banco de dados.
        transacao_id (int): ID da transação a ser modificada.
        transacao (schemas.TransacaoCreate): Novos dados da transação.
        usuario_id (int): ID do usuário que está requisitando a atualização.

    Returns:
        models.Transacao | None: A transação atualizada ou None se não encontrada/não autorizada.
    """
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

def deletar_transacao(
    db: Session, 
    transacao_id: int,
    usuario_id: int
) -> bool:
    """Remove uma transação do banco de dados.

    Args:
        db (Session): Sessão ativa do banco de dados.
        transacao_id (int): ID da transação a ser removida.
        usuario_id (int): ID do usuário solicitante.

    Returns:
        bool: True se removida com sucesso, False caso contrário.
    """
    db_transacao = db.query(models.Transacao).filter(
        models.Transacao.id == transacao_id
    ).first()

    if db_transacao is None:
        return False
        
    if db_transacao.usuario_id != usuario_id:
        return False
        
    db.delete(db_transacao)
    db.commit()
    return True

def listar_transacoes(db: Session, usuario_id: int, skip: int = 0, limit: int = 100) -> list[models.Transacao]:
    """Retorna uma lista paginada das transações de um usuário.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario_id (int): ID do usuário cujas transações serão listadas.
        skip (int): Número de registros a pular (para paginação). Padrão: 0.
        limit (int): Número máximo de registros a retornar. Padrão: 100.

    Returns:
        list[models.Transacao]: Lista de transações encontradas.
    """
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
    """Retorna todas as transações de um usuário em um determinado intervalo de tempo.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario_id (int): ID do usuário.
        data_inicio (date): Data inicial do período (inclusiva).
        data_fim (date): Data final do período (inclusiva).

    Returns:
        list[models.Transacao]: Lista de transações no período.
    """
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


# --- FUNÇÕES ANALÍTICAS (DASHBOARD) ---

def get_dashboard_data(db: Session, usuario_id: int, data_inicio: date, data_fim: date) -> schemas.DashboardData:
    """Calcula e retorna os dados consolidados para o dashboard financeiro.

    Inclui totais de receitas, despesas, lucro líquido e quebras por categoria.

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario_id (int): ID do usuário.
        data_inicio (date): Data inicial do período de análise.
        data_fim (date): Data final do período de análise.

    Returns:
        schemas.DashboardData: Objeto com os dados processados para o dashboard.
    """
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
    
def get_dados_de_tendencia(
    db: Session, 
    usuario_id: int, 
    data_inicio: date, 
    data_fim: date,
    filtro: str
) -> schemas.DadosDeTendencia:
    """Gera dados para gráficos de tendência financeira (evolução temporal).

    Agrupa os dados por dia ou hora, dependendo do filtro selecionado e do
    banco de dados em uso (suporta diferenças de sintaxe entre SQLite e PostgreSQL).

    Args:
        db (Session): Sessão ativa do banco de dados.
        usuario_id (int): ID do usuário.
        data_inicio (date): Data inicial.
        data_fim (date): Data final.
        filtro (str): Granularidade do agrupamento ('daily' para hora, outros para dia).

    Returns:
        schemas.DadosDeTendencia: Dados formatados para plotagem de gráficos.
    """
    data_fim_query = data_fim + timedelta(days=1)
    
    dialect_name = db.bind.dialect.name

    if filtro == 'daily':
        if dialect_name == 'postgresql':
            agrupador_de_data = func.to_char(models.Transacao.data, 'YYYY-MM-DD HH24:00:00')
            ordenador_de_data = func.to_char(models.Transacao.data, 'YYYY-MM-DD HH24:00:00')
        else:
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
