# Arquivo: backend/main.py
"""
Ponto de Entrada Principal da API FastAPI.

Este módulo atua como o Controlador da aplicação, definindo todas as rotas (endpoints),
gerenciando a segurança (autenticação) e as configurações de CORS.

A lógica de negócios e acesso ao banco de dados é delegada para o módulo 'crud.py'.
"""

# --- 1. Importações ---
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError 
from typing import List
from datetime import timedelta, date

from . import crud, models, schemas, security
# Importação de tarefas desabilitada (Arquitetura Síncrona)
# from . import tasks 
from .database import SessionLocal, engine
from .core.config import settings 

# --- 2. Configuração Inicial ---

# Inicializa as tabelas do banco de dados se não existirem.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NOMAD Controle Financeiro API",
    description="API para o aplicativo de controle financeiro NOMAD."
)

# --- 3. Configuração do CORS (Segurança de Navegador) ---

# Configuração de origens permitidas para CORS.
# Permite localhost (desenvolvimento) e subdomínios .vercel.app (produção).
origin_regex = r"https?://(localhost(:\d+)?|.*\.vercel\.app)"

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"], # Permite todos os métodos (GET, POST, PUT, DELETE)
    allow_headers=["*"],
)

# --- 4. Dependências de Segurança e DB ---

# Esquema de autenticação OAuth2 com Bearer Token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    """
    Dependência do FastAPI para gerenciamento de sessão do banco de dados.
    Garante o fechamento da conexão após cada requisição.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Dependência de autenticação.
    
    Valida o token JWT, busca o usuário correspondente no banco de dados
    e retorna o objeto usuário. Lança exceção HTTP 401 se inválido.
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


# --- 5. ENDPOINTS (Autenticação) ---

@app.post("/token", response_model=schemas.Token, summary="Login do Usuário")
def login_para_obter_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    Autentica o usuário verificando nome de usuário e senha.
    Retorna um Token JWT de acesso se as credenciais forem válidas.
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
    """
    Registra um novo usuário no sistema.
    Verifica duplicidade de nome de usuário antes da criação.
    """
    db_usuario = crud.get_usuario_por_nome(db, nome_usuario=usuario.nome_usuario)
    if db_usuario:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome de usuário já registrado")
    
    # Criação do usuário e hash da senha são tratados no service layer
    return crud.criar_usuario(db=db, usuario=usuario)

@app.get("/", summary="Endpoint Raiz (Health Check)")
def ler_raiz():
    """Endpoint público para verificar se a API está online."""
    return {"message": "Bem-vindo à API de Controle Financeiro!"}


# --- 6. ENDPOINTS DE PERFIL DE USUÁRIO (V7.0) ---

@app.get("/usuarios/me", response_model=schemas.Usuario, summary="Ler Perfil do Usuário Logado")
def ler_perfil_do_usuario(
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """
    Retorna os dados do perfil do usuário autenticado.
    """
    return usuario_atual

@app.put("/usuarios/me", response_model=schemas.Usuario, summary="Atualizar Perfil do Usuário")
def atualizar_perfil_do_usuario(
    detalhes: schemas.UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """
    Atualiza as informações do perfil do usuário autenticado.
    """
    try:
        return crud.atualizar_detalhes_usuario(
            db=db, 
            usuario=usuario_atual, 
            detalhes=detalhes
        )
    except IntegrityError:
        # Trata violação de unicidade (nome de usuário ou email já existentes)
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
    """
    Atualiza a senha do usuário, verificando a senha antiga primeiro.
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

# --- 7. ENDPOINTS (Relatórios e Dashboard) ---
@app.get("/dashboard/", response_model=schemas.DashboardData, summary="Ler Dados do Dashboard")
def ler_dados_dashboard(
    data_inicio: date, 
    data_fim: date, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Retorna os dados consolidados para os cards e gráficos do Dashboard."""
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
    """
    Retorna os dados de tendência (Receita vs. Despesa), agrupados
    por HORA (se filtro='daily') ou por DIA (outros filtros).
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
    """Retorna a lista detalhada de transações dentro de um período."""
    transacoes = crud.listar_transacoes_por_periodo(
        db=db, 
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    return transacoes

# --- 8. ENDPOINTS DE TRANSAÇÃO (SÍNCRONO) ---
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
    """
    Cria uma nova transação e retorna os dados atualizados do dashboard.
    """
    db_transacao = crud.criar_transacao(
        db=db, 
        transacao=transacao, 
        usuario_id=usuario_atual.id
    )
    
    # Recálculo dos dados do dashboard
    dashboard_data = crud.get_dashboard_data(
        db=db,
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    return dashboard_data

# (Endpoint /transacoes/sync foi removido na V9.3)

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
    """
    Atualiza uma transação existente e retorna os dados atualizados do dashboard.
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
    """
    Remove uma transação e retorna os dados atualizados do dashboard.
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
    """Retorna uma lista paginada das transações mais recentes."""
    transacoes = crud.listar_transacoes(db, usuario_id=usuario_atual.id, skip=skip, limit=limit)
    return transacoes

# --- 9. ENDPOINTS DE CATEGORIA ---
@app.post("/categorias/", response_model=schemas.Categoria, summary="Criar Categoria")
def criar_nova_categoria(
    categoria: schemas.CategoriaCreate, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Cria uma nova categoria (nome, tipo, cor)."""
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
    """Lista todas as categorias disponíveis."""
    categorias = crud.listar_categorias(db=db)
    return categorias
@app.put("/categorias/{categoria_id}", response_model=schemas.Categoria, summary="Editar Categoria (PATCH)")
def editar_categoria(
    categoria_id: int,
    categoria: schemas.CategoriaUpdate, # Usa o schema 'Update' (parcial)
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """Atualiza parcialmente uma categoria (nome, tipo ou cor)."""
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
    """Deleta uma categoria (se não estiver em uso)."""
    try:
        sucesso = crud.deletar_categoria(db=db, categoria_id=categoria_id)
        if not sucesso:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada")
    except IntegrityError:
        db.rollback()
        # Impede exclusão se a categoria estiver vinculada a transações
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir: Esta categoria já está sendo usada por transações."
        )
    return {"message": "Categoria deletada com sucesso."}