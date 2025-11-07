# Arquivo: backend/main.py (VERSÃO V7.2 - COMPLETA)
"""
CHECK-UP (V7.2): Adiciona 'try/except IntegrityError'
no endpoint 'atualizar_perfil_do_usuario' para
capturar o erro "username já existe" (V7.2).
"""

# --- 1. Importações ---
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
# IMPORTAÇÃO NECESSÁRIA PARA O TRATAMENTO DE ERRO
from sqlalchemy.exc import IntegrityError 
from typing import List
from datetime import timedelta, date

from . import crud, models, schemas, security
from . import tasks 
from .database import SessionLocal, engine
from .core.config import settings 

# --- (Configuração, CORS, Dependências - Sem mudança) ---
models.Base.metadata.create_all(bind=engine)
app = FastAPI()
origins = [
    "http://localhost:5173",
    "http://localhost:4173",
    "https://controle-financeiro-api-eight.vercel.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def get_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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
# (Sem mudanças)
@app.post("/token", response_model=schemas.Token)
def login_para_obter_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
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

@app.post("/usuarios/", response_model=schemas.Usuario)
def criar_novo_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    db_usuario = crud.get_usuario_por_nome(db, nome_usuario=usuario.nome_usuario)
    if db_usuario:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome de usuário já registrado")
    return crud.criar_usuario(db=db, usuario=usuario)

@app.get("/")
def ler_raiz():
    return {"message": "Bem-vindo à API de Controle Financeiro!"}


# --- 6. ENDPOINTS DE PERFIL DE USUÁRIO (ATUALIZADO) ---

@app.get("/usuarios/me", response_model=schemas.Usuario)
def ler_perfil_do_usuario(
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    return usuario_atual

@app.put("/usuarios/me", response_model=schemas.Usuario)
def atualizar_perfil_do_usuario(
    detalhes: schemas.UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """
    Atualiza os detalhes do perfil do usuário logado.
    (V7.2: Adiciona tratamento de erro para 'nome_usuario' duplicado)
    """
    try:
        return crud.atualizar_detalhes_usuario(
            db=db, 
            usuario=usuario_atual, 
            detalhes=detalhes
        )
    except IntegrityError:
        # (O 'crud.py' já é agnóstico, mas a 'IntegrityError'
        #  acontece aqui se o 'nome_usuario' já estiver em uso)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esse nome de usuário já está em uso."
        )

@app.post("/usuarios/mudar-senha")
def mudar_senha(
    payload: schemas.UsuarioChangePassword,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
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
# (Sem mudanças)
@app.get("/dashboard/", response_model=schemas.DashboardData)
def ler_dados_dashboard(
    data_inicio: date, 
    data_fim: date, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    return crud.get_dashboard_data(
        db=db, 
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio, 
        data_fim=data_fim
    )
@app.get("/relatorios/tendencia", response_model=schemas.DadosDeTendencia)
def ler_dados_de_tendencia(
    data_inicio: date, 
    data_fim: date, 
    filtro: str = Query("monthly", alias="filtro"),
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    return crud.get_dados_de_tendencia(
        db=db, 
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio, 
        data_fim=data_fim,
        filtro=filtro 
    ) 
@app.get("/transacoes/periodo/", response_model=List[schemas.Transacao])
def ler_transacoes_por_periodo(
    data_inicio: date, 
    data_fim: date, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    transacoes = crud.listar_transacoes_por_periodo(
        db=db, 
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    return transacoes

# --- 8. ENDPOINTS (Transação) ---
# (Sem mudanças)
@app.post("/transacoes/", 
    response_model=schemas.Transacao,
    status_code=status.HTTP_201_CREATED
)
def criar_nova_transacao(
    transacao: schemas.TransacaoCreate, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    db_transacao = crud.criar_transacao(
        db=db, 
        transacao=transacao, 
        usuario_id=usuario_atual.id
    )
    tasks.task_recalculate_dashboard.delay(usuario_id=usuario_atual.id)
    return db_transacao
@app.put("/transacoes/{transacao_id}", response_model=schemas.Transacao)
def editar_transacao(
    transacao_id: int,
    transacao: schemas.TransacaoCreate,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    db_transacao = crud.atualizar_transacao(
        db=db,
        transacao_id=transacao_id,
        transacao=transacao,
        usuario_id=usuario_atual.id
    )
    if db_transacao is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada ou não pertence ao usuário")
    tasks.task_recalculate_dashboard.delay(usuario_id=usuario_atual.id)
    return db_transacao
@app.get("/transacoes/", response_model=List[schemas.Transacao])
def ler_transacoes(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    transacoes = crud.listar_transacoes(db, usuario_id=usuario_atual.id, skip=skip, limit=limit)
    return transacoes
@app.post("/categorias/", response_model=schemas.Categoria)
def criar_nova_categoria(
    categoria: schemas.CategoriaCreate, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    return crud.criar_categoria(db=db, categoria=categoria)
@app.get("/categorias/", response_model=List[schemas.Categoria])
def ler_categorias(
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    categorias = crud.listar_categorias(db=db)
    return categorias