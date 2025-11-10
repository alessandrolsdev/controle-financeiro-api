# Arquivo: backend/crud.py
"""
Módulo CRUD (Create, Read, Update, Delete) - A Camada de Serviço (Service Layer).

Este módulo centraliza toda a lógica de negócios e interação direta
com o banco de dados (SQLAlchemy). Ele é chamado pelo 'main.py' (Controlador)
para manter a separação de responsabilidades (SoC).

Responsabilidades:
- Hashing e verificação de senhas.
- Lógica de banco de dados (Queries) para Usuários, Categorias e Transações.
- Funções analíticas (OLAP) para geração de relatórios (Dashboard, Tendências).
"""

# --- 1. Importações ---
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, cast, Date 
from sqlalchemy.exc import IntegrityError 
from datetime import date, timedelta
import decimal

from . import models, schemas, security

# --- 2. FUNÇÕES CRUD (USUÁRIO) ---

def get_usuario_por_nome(db: Session, nome_usuario: str) -> models.Usuario | None:
    """
    Busca um usuário no banco de dados pelo nome de usuário.

    Args:
        db (Session): A sessão do SQLAlchemy.
        nome_usuario (str): O nome de usuário a ser buscado.

    Returns:
        models.Usuario | None: O objeto do usuário se encontrado, senão None.
    """
    return db.query(models.Usuario).filter(models.Usuario.nome_usuario == nome_usuario).first()

def criar_usuario(db: Session, usuario: schemas.UsuarioCreate) -> models.Usuario:
    """
    Cria um novo usuário no banco de dados com uma senha hasheada.

    Args:
        db (Session): A sessão do SQLAlchemy.
        usuario (schemas.UsuarioCreate): Os dados do novo usuário (com senha em texto plano).

    Returns:
        models.Usuario: O objeto do usuário recém-criado.
    """
    # Delega a geração de hash para o módulo 'security'
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
    """
    Atualiza (PATCH) os campos de perfil de um objeto de usuário existente.
    'exclude_unset=True' garante que apenas os campos enviados
    (ex: só 'email') sejam atualizados, preservando os existentes.

    Args:
        db (Session): A sessão do SQLAlchemy.
        usuario (models.Usuario): O objeto de usuário (obtido via 'get_usuario_atual').
        detalhes (schemas.UsuarioUpdate): Um schema Pydantic com os campos opcionais.

    Returns:
        models.Usuario: O objeto do usuário atualizado.
    """
    # 'exclude_unset=True' é a chave para a lógica de PATCH (atualização parcial).
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
    """
    Verifica a senha antiga e, se correta, atualiza para a nova senha.

    Args:
        db (Session): A sessão do SQLAlchemy.
        usuario (models.Usuario): O objeto de usuário logado.
        payload (schemas.UsuarioChangePassword): Contém a senha antiga e a nova.

    Returns:
        bool: True se a senha foi alterada, False se a senha antiga estava incorreta.
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

# --- 3. FUNÇÕES CRUD (CATEGORIA) ---

def criar_categoria(db: Session, categoria: schemas.CategoriaCreate) -> models.Categoria:
    """
    Cria uma nova categoria (nome, tipo, cor).
    (Levanta IntegrityError se o nome for duplicado).
    
    Args:
        db (Session): A sessão do SQLAlchemy.
        categoria (schemas.CategoriaCreate): Dados da nova categoria.

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
    (Usado para preencher os dropdowns no frontend).

    Args:
        db (Session): A sessão do SQLAlchemy.

    Returns:
        list[models.Categoria]: Uma lista de todos os objetos de categoria.
    """
    return db.query(models.Categoria).all()

def atualizar_categoria(
    db: Session, 
    categoria_id: int, 
    categoria_update: schemas.CategoriaUpdate
) -> models.Categoria | None:
    """
    Atualiza (PATCH) uma categoria existente (nome, tipo ou cor).
    Apenas atualiza os campos que foram enviados.

    Args:
        db (Session): A sessão do SQLAlchemy.
        categoria_id (int): O ID da categoria a ser editada.
        categoria_update (schemas.CategoriaUpdate): Os campos opcionais a serem alterados.

    Returns:
        models.Categoria | None: O objeto atualizado, ou None se não encontrado.
    """
    db_categoria = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
    if not db_categoria:
        return None # 404
        
    update_data = categoria_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_categoria, key, value)
        
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

def deletar_categoria(db: Session, categoria_id: int) -> bool:
    """
    Deleta uma categoria.
    
    Args:
        db (Session): A sessão do SQLAlchemy.
        categoria_id (int): O ID da categoria a ser deletada.

    Returns:
        bool: True se deletou, False se não encontrou.
        
    Raises:
        IntegrityError: (Capturado pelo main.py) Se a categoria
                        estiver em uso por uma transação (ForeignKey constraint).
    """
    db_categoria = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
    if not db_categoria:
        return False # 404
    
    db.delete(db_categoria)
    db.commit()
    return True

# --- 4. FUNÇÕES CRUD (TRANSAÇÃO) ---

def criar_transacao(db: Session, transacao: schemas.TransacaoCreate, usuario_id: int) -> models.Transacao:
    """
    Cria uma nova transação (gasto ou receita) no banco, associada a um usuário.

    Args:
        db (Session): A sessão do SQLAlchemy.
        transacao (schemas.TransacaoCreate): Os dados da nova transação.
        usuario_id (int): O ID do usuário (do token) que está registrando.

    Returns:
        models.Transacao: O objeto da transação recém-criada.
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
    """
    Atualiza uma transação existente, verificando a posse (usuário).

    Args:
        db (Session): A sessão do SQLAlchemy.
        transacao_id (int): O ID da transação a ser editada.
        transacao (schemas.TransacaoCreate): Os novos dados (completos) do formulário.
        usuario_id (int): O ID do usuário logado (para verificação de segurança).

    Returns:
        models.Transacao | None: O objeto atualizado, ou None se não encontrado/não autorizado.
    """
    db_transacao = db.query(models.Transacao).filter(
        models.Transacao.id == transacao_id
    ).first()

    if db_transacao is None:
        return None # 404
    
    # VERIFICAÇÃO DE SEGURANÇA (CRÍTICA!):
    if db_transacao.usuario_id != usuario_id:
        return None # 404/403
        
    # Atualiza os campos (lógica de PUT, não PATCH)
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
    """
    Deleta uma transação, verificando a posse (usuário).

    Args:
        db (Session): A sessão do SQLAlchemy.
        transacao_id (int): O ID da transação a ser deletada.
        usuario_id (int): O ID do usuário logado (para verificação de segurança).

    Returns:
        bool: True se deletou, False se não encontrou/não autorizado.
    """
    db_transacao = db.query(models.Transacao).filter(
        models.Transacao.id == transacao_id
    ).first()

    if db_transacao is None:
        return False # 404
        
    if db_transacao.usuario_id != usuario_id:
        return False # 404/403
        
    db.delete(db_transacao)
    db.commit()
    return True

def listar_transacoes(db: Session, usuario_id: int, skip: int = 0, limit: int = 100) -> list[models.Transacao]:
    """
    Retorna uma lista de transações com paginação, filtrada por usuário.
    (Usado para o card "Últimas 5 Transações").
    
    Decisão de Engenharia (N+1):
    Usamos 'options(joinedload(models.Transacao.categoria))' (Eager Loading)
    para forçar o SQLAlchemy a fazer um JOIN. Isso garante que o
    frontend receba 'transacao.categoria.nome' e 'transacao.categoria.cor'
    em uma única query, resolvendo o problema N+1.
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
    """
    Retorna TODAS as transações de um usuário dentro de um período.
    (Usado pelo card "Transações no Período" e pela exportação Excel).
    
    Decisão de Engenharia (N+1):
    Também usa 'joinedload' para garantir que o frontend
    receba os dados completos da categoria.
    """
    # Adiciona +1 dia ao 'data_fim' para incluir
    # todas as horas do último dia (ex: 06/11 23:59)
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


# --- 5. FUNÇÃO DO DASHBOARD (OLAP) ---

def get_dashboard_data(db: Session, usuario_id: int, data_inicio: date, data_fim: date) -> schemas.DashboardData:
    """
    Busca e calcula os dados de resumo financeiro (OLAP)
    para o Dashboard e a página de Relatórios.
    
    Esta é a função "lenta" que é chamada de forma síncrona
    no nosso deploy gratuito (V-Revert).
    """
    data_fim_query = data_fim + timedelta(days=1)

    # 1. Total de Receitas
    total_receitas = db.query(func.sum(models.Transacao.valor)).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Receita",
        models.Transacao.data >= data_inicio,
        models.Transacao.data < data_fim_query
    ).scalar() or decimal.Decimal(0)

    # 2. Total de Gastos
    total_gastos = db.query(func.sum(models.Transacao.valor)).join(models.Categoria).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Categoria.tipo == "Gasto",
        models.Transacao.data >= data_inicio,
        models.Transacao.data < data_fim_query
    ).scalar() or decimal.Decimal(0)

    # 3. Lucro Líquido (em Python)
    lucro_liquido = total_receitas - total_gastos

    # 4. Gastos Detalhados (Agrupados por Categoria)
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
    
    # 5. Receitas Detalhadas (Agrupadas por Categoria)
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

    # 6. Formata os resultados para o schema
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

    # 7. Retorna o objeto de dados completo
    return schemas.DashboardData(
        total_receitas=total_receitas,
        total_gastos=total_gastos,
        lucro_liquido=lucro_liquido,
        gastos_por_categoria=gastos_por_categoria,
        receitas_por_categoria=receitas_por_categoria
    )
    
# --- 6. FUNÇÃO DE RELATÓRIOS (OLAP) ---

def get_dados_de_tendencia(
    db: Session, 
    usuario_id: int, 
    data_inicio: date, 
    data_fim: date,
    filtro: str
) -> schemas.DadosDeTendencia:
    """
    Busca e calcula os dados de Receitas e Despesas agrupados
    POR HORA (se filtro='daily') ou POR DIA (outros filtros).
    
    Decisão de Engenharia (Dialeto SQL):
    Esta função é "bilíngue". Ela checa o dialeto do banco de dados
    para usar a sintaxe de formatação de data correta,
    garantindo que funcione tanto em SQLite (dev) quanto em PostgreSQL (prod).
    """
    data_fim_query = data_fim + timedelta(days=1)
    
    dialect_name = db.bind.dialect.name

    if filtro == 'daily':
        if dialect_name == 'postgresql':
            # Sintaxe do POSTGRESQL (Produção)
            agrupador_de_data = func.to_char(models.Transacao.data, 'YYYY-MM-DD HH24:00:00')
            ordenador_de_data = func.to_char(models.Transacao.data, 'YYYY-MM-DD HH24:00:00')
        else:
            # Sintaxe do SQLITE (Desenvolvimento)
            agrupador_de_data = func.strftime('%Y-%m-%d %H:00:00', models.Transacao.data)
            ordenador_de_data = func.strftime('%Y-%m-%d %H:00:00', models.Transacao.data)
    else:
        # Agrupamento por DIA (func.date) é universal
        agrupador_de_data = func.date(models.Transacao.data)
        ordenador_de_data = func.date(models.Transacao.data)

    # --- Subconsulta 1: Receitas agrupadas ---
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

    # --- Subconsulta 2: Despesas agrupadas ---
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