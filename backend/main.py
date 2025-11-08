# Arquivo: backend/main.py (VERSÃO COMPLETA V9.0)
"""
CHECK-UP (V9.0): Adiciona o novo endpoint 'DELETE /transacoes/{transacao_id}'.
Ele é SÍNCRONO (como POST e PUT) e retorna o DashboardData atualizado.
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
# 'tasks' foi removido
from .database import SessionLocal, engine
from .core.config import settings 

# --- 2. Configuração Inicial ---
models.Base.metadata.create_all(bind=engine)
app = FastAPI()

# --- 3. Configuração do CORS ---
origin_regex = r"https?://(localhost(:\d+)?|.*\.vercel\.app)"
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# --- 4. Dependências de Segurança ---
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


# --- 6. ENDPOINTS DE PERFIL DE USUÁRIO (V7.0) ---
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

# --- 8. ENDPOINTS DE TRANSAÇÃO (ATUALIZADO V9.0) ---
@app.post("/transacoes/", 
    response_model=schemas.DashboardData
)
def criar_nova_transacao(
    transacao: schemas.TransacaoCreate, 
    data_inicio: date, 
    data_fim: date,
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
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
    response_model=schemas.DashboardData
)
def editar_transacao(
    transacao_id: int,
    transacao: schemas.TransacaoCreate,
    data_inicio: date, 
    data_fim: date,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada")
    dashboard_data = crud.get_dashboard_data(
        db=db,
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    return dashboard_data

# --- O NOVO ENDPOINT DE EXCLUSÃO (V9.0) ---
# (Ele é SÍNCRONO, como o POST e o PUT)
@app.delete("/transacoes/{transacao_id}", response_model=schemas.DashboardData)
def deletar_transacao_e_recalcular(
    transacao_id: int,
    data_inicio: date, 
    data_fim: date,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """
    Deleta uma transação e retorna o dashboard atualizado.
    """
    # 1. Deleta a transação
    sucesso = crud.deletar_transacao(
        db=db,
        transacao_id=transacao_id,
        usuario_id=usuario_atual.id
    )
    if not sucesso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada")
        
    # 2. Recalcula o dashboard (Síncrono)
    dashboard_data = crud.get_dashboard_data(
        db=db,
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    return dashboard_data
# ---------------------------------------------

@app.get("/transacoes/", response_model=List[schemas.Transacao])
def ler_transacoes(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    transacoes = crud.listar_transacoes(db, usuario_id=usuario_atual.id, skip=skip, limit=limit)
    return transacoes

# --- 9. ENDPOINTS DE CATEGORIA (V8.0) ---
@app.post("/categorias/", response_model=schemas.Categoria)
def criar_nova_categoria(
    categoria: schemas.CategoriaCreate, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    try:
        return crud.criar_categoria(db=db, categoria=categoria)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uma categoria com este nome já existe."
        )

@app.get("/categorias/", response_model=List[schemas.Categoria])
def ler_categorias(
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    categorias = crud.listar_categorias(db=db)
    return categorias

@app.put("/categorias/{categoria_id}", response_model=schemas.Categoria)
def editar_categoria(
    categoria_id: int,
    categoria: schemas.CategoriaUpdate,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
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

@app.delete("/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_categoria_endpoint( # Nomeado 'deletar_categoria_endpoint' para evitar conflito com a importação
    categoria_id: int,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
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