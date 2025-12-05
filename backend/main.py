# Arquivo: backend/main.py
"""Módulo Principal da Aplicação FastAPI.

Este módulo inicializa a aplicação FastAPI, configura o middleware CORS,
define as dependências de injeção e registra todas as rotas (endpoints)
da API.

Responsabilidades:
- Inicialização da aplicação.
- Configuração de middlewares (CORS).
- Gestão de autenticação via OAuth2.
- Definição de endpoints para Usuários, Transações, Categorias e Relatórios.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError 
from typing import List
from datetime import timedelta, date

from . import crud, models, schemas, security
from .database import SessionLocal, engine
from .core.config import settings 

# --- Configuração Inicial ---

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NOMAD Controle Financeiro API",
    description="API para o aplicativo de controle financeiro NOMAD."
)

# --- Configuração do CORS ---

origin_regex = r"https?://(localhost(:\d+)?|.*\.vercel\.app)"

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependências ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    """Gerenciador de contexto para sessões do banco de dados.

    Cria uma nova sessão para cada requisição e garante seu fechamento ao final.

    Yields:
        Session: A sessão do banco de dados SQLAlchemy.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Verifica e retorna o usuário autenticado atual.

    Decodifica o token JWT fornecido no header de autorização e busca o usuário
    correspondente no banco de dados.

    Args:
        token (str): O token JWT Bearer.
        db (Session): Sessão do banco de dados.

    Raises:
        HTTPException: Se o token for inválido, expirado ou o usuário não existir.

    Returns:
        models.Usuario: O objeto do usuário autenticado.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = security.verificar_token_de_acesso(token, credentials_exception)
    usuario = crud.get_usuario_por_nome(db, nome_usuario=token_data.nome_usuario)
    if usuario is None:
        raise credentials_exception
    return usuario


# --- ENDPOINTS (Autenticação) ---

@app.post("/token", response_model=schemas.Token, summary="Login do Usuário")
def login_para_obter_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """Autentica um usuário e retorna um token de acesso JWT.

    Verifica se o nome de usuário e a senha correspondem a um registro válido.

    Args:
        form_data (OAuth2PasswordRequestForm): Dados do formulário de login (username, password).
        db (Session): Sessão do banco de dados.

    Raises:
        HTTPException: Se as credenciais forem inválidas.

    Returns:
        dict: Um dicionário contendo o token de acesso e o tipo do token.
    """
    usuario = crud.get_usuario_por_nome(db, nome_usuario=form_data.username)
    if not usuario or not security.verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token = security.criar_token_de_acesso(
        data={"sub": usuario.nome_usuario}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/usuarios/", response_model=schemas.Usuario, status_code=status.HTTP_201_CREATED, summary="Criar Novo Usuário (Signup)")
def criar_novo_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    """Registra um novo usuário na plataforma.

    Args:
        usuario (schemas.UsuarioCreate): Dados para criação do usuário.
        db (Session): Sessão do banco de dados.

    Raises:
        HTTPException: Se o nome de usuário já estiver em uso.

    Returns:
        models.Usuario: O usuário criado.
    """
    db_usuario = crud.get_usuario_por_nome(db, nome_usuario=usuario.nome_usuario)
    if db_usuario:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome de usuário já registrado")
    
    return crud.criar_usuario(db=db, usuario=usuario)

@app.get("/", summary="Endpoint Raiz (Health Check)")
def ler_raiz():
    """Verifica se a API está operacional.

    Returns:
        dict: Mensagem de boas-vindas.
    """
    return {"message": "Bem-vindo à API de Controle Financeiro!"}


# --- ENDPOINTS DE PERFIL DE USUÁRIO ---

@app.get("/usuarios/me", response_model=schemas.Usuario, summary="Ler Perfil do Usuário Logado")
def ler_perfil_do_usuario(
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Retorna as informações do perfil do usuário atualmente autenticado.

    Args:
        usuario_atual (models.Usuario): Usuário obtido via token.

    Returns:
        models.Usuario: O objeto usuário.
    """
    return usuario_atual

@app.put("/usuarios/me", response_model=schemas.Usuario, summary="Atualizar Perfil do Usuário")
def atualizar_perfil_do_usuario(
    detalhes: schemas.UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Atualiza as informações cadastrais do usuário logado.

    Args:
        detalhes (schemas.UsuarioUpdate): Dados a serem atualizados.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Raises:
        HTTPException: Se houver conflito de dados únicos (ex: email).

    Returns:
        models.Usuario: O usuário com os dados atualizados.
    """
    try:
        return crud.atualizar_detalhes_usuario(
            db=db, 
            usuario=usuario_atual, 
            detalhes=detalhes
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esse nome de usuário ou email já está em uso."
        )

@app.post("/usuarios/mudar-senha", summary="Alterar Senha")
def mudar_senha(
    payload: schemas.UsuarioChangePassword,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Altera a senha de acesso do usuário.

    Args:
        payload (schemas.UsuarioChangePassword): Senha atual e nova senha.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Raises:
        HTTPException: Se a senha atual estiver incorreta.

    Returns:
        dict: Mensagem de sucesso.
    """
    sucesso = crud.mudar_senha_usuario(
        db=db, 
        usuario=usuario_atual, 
        payload=payload
    )
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="A senha antiga está incorreta."
        )
    return {"message": "Senha atualizada com sucesso."}

# --- ENDPOINTS (Relatórios e Dashboard) ---

@app.get("/dashboard/", response_model=schemas.DashboardData, summary="Ler Dados do Dashboard")
def ler_dados_dashboard(
    data_inicio: date, 
    data_fim: date, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Obtém o resumo financeiro para o dashboard.

    Args:
        data_inicio (date): Início do período.
        data_fim (date): Fim do período.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Returns:
        schemas.DashboardData: Dados consolidados de receitas, despesas e categorias.
    """
    return crud.get_dashboard_data(
        db=db, 
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio, 
        data_fim=data_fim
    )

@app.get("/relatorios/tendencia", response_model=schemas.DadosDeTendencia, summary="Ler Dados do Gráfico de Linha")
def ler_dados_de_tendencia(
    data_inicio: date, 
    data_fim: date, 
    filtro: str = Query("monthly", alias="filtro"),
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Obtém dados para gráficos de tendência (evolução temporal).

    Args:
        data_inicio (date): Início do período.
        data_fim (date): Fim do período.
        filtro (str): Granularidade ('daily' para hora, outros para dia).
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Returns:
        schemas.DadosDeTendencia: Séries temporais de receitas e despesas.
    """
    return crud.get_dados_de_tendencia(
        db=db, 
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio, 
        data_fim=data_fim,
        filtro=filtro 
    ) 

@app.get("/transacoes/periodo/", response_model=List[schemas.Transacao], summary="Listar Transações por Período")
def ler_transacoes_por_periodo(
    data_inicio: date, 
    data_fim: date, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Lista todas as transações dentro de um intervalo de datas.

    Args:
        data_inicio (date): Início do período.
        data_fim (date): Fim do período.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Returns:
        List[schemas.Transacao]: Lista de transações encontradas.
    """
    transacoes = crud.listar_transacoes_por_periodo(
        db=db, 
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    return transacoes

# --- ENDPOINTS DE TRANSAÇÃO (SÍNCRONO) ---

@app.post("/transacoes/", 
    response_model=schemas.DashboardData,
    summary="Criar Transação (Síncrono)"
)
def criar_nova_transacao(
    transacao: schemas.TransacaoCreate, 
    data_inicio: date, 
    data_fim: date,
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Cria uma nova transação e retorna os dados do dashboard atualizados.

    Args:
        transacao (schemas.TransacaoCreate): Dados da nova transação.
        data_inicio (date): Início do período para recálculo do dashboard.
        data_fim (date): Fim do período para recálculo do dashboard.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Returns:
        schemas.DashboardData: Dados atualizados do dashboard.
    """
    db_transacao = crud.criar_transacao(
        db=db, 
        transacao=transacao, 
        usuario_id=usuario_atual.id
    )
    
    dashboard_data = crud.get_dashboard_data(
        db=db,
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    return dashboard_data


@app.put("/transacoes/{transacao_id}", 
    response_model=schemas.DashboardData,
    summary="Editar Transação (Síncrono)"
)
def editar_transacao(
    transacao_id: int,
    transacao: schemas.TransacaoCreate,
    data_inicio: date, 
    data_fim: date,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Edita uma transação existente e atualiza o dashboard.

    Args:
        transacao_id (int): ID da transação a ser editada.
        transacao (schemas.TransacaoCreate): Novos dados da transação.
        data_inicio (date): Início do período.
        data_fim (date): Fim do período.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Raises:
        HTTPException: Se a transação não for encontrada ou não pertencer ao usuário.

    Returns:
        schemas.DashboardData: Dados atualizados do dashboard.
    """
    db_transacao = crud.atualizar_transacao(
        db=db,
        transacao_id=transacao_id,
        transacao=transacao,
        usuario_id=usuario_atual.id
    )
    if db_transacao is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada")
    
    dashboard_data = crud.get_dashboard_data(
        db=db,
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    return dashboard_data

@app.delete("/transacoes/{transacao_id}", response_model=schemas.DashboardData, summary="Deletar Transação (Síncrono)")
def deletar_transacao_e_recalcular(
    transacao_id: int,
    data_inicio: date, 
    data_fim: date,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Remove uma transação e atualiza o dashboard.

    Args:
        transacao_id (int): ID da transação a ser removida.
        data_inicio (date): Início do período.
        data_fim (date): Fim do período.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Raises:
        HTTPException: Se a transação não for encontrada.

    Returns:
        schemas.DashboardData: Dados atualizados do dashboard.
    """
    sucesso = crud.deletar_transacao(
        db=db,
        transacao_id=transacao_id,
        usuario_id=usuario_atual.id
    )
    if not sucesso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada")
        
    dashboard_data = crud.get_dashboard_data(
        db=db,
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    return dashboard_data

@app.get("/transacoes/", response_model=List[schemas.Transacao], summary="Listar Últimas Transações (Paginado)")
def ler_transacoes(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Lista as transações mais recentes com paginação.

    Args:
        skip (int): Quantidade de registros a pular.
        limit (int): Máximo de registros a retornar.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Returns:
        List[schemas.Transacao]: Lista de transações.
    """
    transacoes = crud.listar_transacoes(db, usuario_id=usuario_atual.id, skip=skip, limit=limit)
    return transacoes

# --- ENDPOINTS DE CATEGORIA ---

@app.post("/categorias/", response_model=schemas.Categoria, summary="Criar Categoria")
def criar_nova_categoria(
    categoria: schemas.CategoriaCreate, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Cria uma nova categoria.

    Args:
        categoria (schemas.CategoriaCreate): Dados da nova categoria.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Raises:
        HTTPException: Se já existir uma categoria com o mesmo nome.

    Returns:
        schemas.Categoria: A categoria criada.
    """
    try:
        return crud.criar_categoria(db=db, categoria=categoria)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uma categoria com este nome já existe."
        )

@app.get("/categorias/", response_model=List[schemas.Categoria], summary="Listar Categorias")
def ler_categorias(
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Retorna todas as categorias disponíveis.

    Args:
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Returns:
        List[schemas.Categoria]: Lista de todas as categorias.
    """
    categorias = crud.listar_categorias(db=db)
    return categorias

@app.put("/categorias/{categoria_id}", response_model=schemas.Categoria, summary="Editar Categoria (PATCH)")
def editar_categoria(
    categoria_id: int,
    categoria: schemas.CategoriaUpdate,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Atualiza parcialmente uma categoria.

    Args:
        categoria_id (int): ID da categoria.
        categoria (schemas.CategoriaUpdate): Dados a serem atualizados.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Raises:
        HTTPException: Se houver conflito de nome ou categoria não encontrada.

    Returns:
        schemas.Categoria: A categoria atualizada.
    """
    try:
        db_categoria = crud.atualizar_categoria(
            db=db,
            categoria_id=categoria_id,
            categoria_update=categoria
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uma categoria com este nome já existe."
        )
    if db_categoria is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada")
    return db_categoria

@app.delete("/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar Categoria")
def deletar_categoria_endpoint(
    categoria_id: int,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Remove uma categoria do sistema.

    Args:
        categoria_id (int): ID da categoria.
        db (Session): Sessão do banco de dados.
        usuario_atual (models.Usuario): Usuário autenticado.

    Raises:
        HTTPException: Se a categoria não for encontrada ou estiver em uso.

    Returns:
        dict: Mensagem de sucesso.
    """
    try:
        sucesso = crud.deletar_categoria(db=db, categoria_id=categoria_id)
        if not sucesso:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir: Esta categoria já está sendo usada por transações."
        )
    return {"message": "Categoria deletada com sucesso."}
