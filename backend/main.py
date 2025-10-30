# Arquivo: backend/main.py (Versão Completa e Verificada)

# --- Importações ---
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta
from datetime import timedelta, date

from . import crud, models, schemas, security
from .database import SessionLocal, engine

# --- Configuração Inicial ---
models.Base.metadata.create_all(bind=engine)
app = FastAPI()

# --- Esquema de Segurança (A fechadura) ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Dependências e Funções Auxiliares ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- O "SEGURANÇA": Função para obter o usuário logado ---
def get_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Precisamos importar 'schemas' aqui no 'security.py' ou passar 'schemas.TokenData'
    # Vamos garantir que a importação 'from . import schemas' esteja em security.py
    token_data = security.verificar_token_de_acesso(token, credentials_exception)
    usuario = crud.get_usuario_por_nome(db, nome_usuario=token_data.nome_usuario)
    if usuario is None:
        raise credentials_exception
    return usuario


# --- ENDPOINTS DE AUTENTICAÇÃO E USUÁRIOS ---

@app.post("/token", response_model=schemas.Token)
def login_para_obter_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Endpoint de login. Recebe usuário e senha, retorna um token de acesso.
    """
    usuario = crud.get_usuario_por_nome(db, nome_usuario=form_data.username)
    if not usuario or not security.verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.criar_token_de_acesso(
        data={"sub": usuario.nome_usuario}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/usuarios/", response_model=schemas.Usuario)
def criar_novo_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    """
    Endpoint para criar um novo usuário. (Este endpoint é público).
    """
    db_usuario = crud.get_usuario_por_nome(db, nome_usuario=usuario.nome_usuario)
    if db_usuario:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome de usuário já registrado")
    
    return crud.criar_usuario(db=db, usuario=usuario)


# --- ENDPOINTS DE TRANSAÇÕES ---

@app.get("/transacoes/", response_model=List[schemas.Transacao])
def ler_transacoes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    """
    Cria uma nova transação. Requer autenticação.
    O ID do usuário é pego automaticamente do token de acesso.
    """
    return crud.criar_transacao(db=db, transacao=transacao, usuario_id=usuario_atual.id)


@app.get("/transacoes/", response_model=List[schemas.Transacao])
def ler_transacoes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Endpoint para listar todas as transações existentes. (Atualmente público)
    """
    transacoes = crud.listar_transacoes(db, skip=skip, limit=limit)
    return transacoes

@app.get("/dashboard/", response_model=schemas.DashboardData)
def ler_dados_dashboard(
    data_inicio: date, 
    data_fim: date, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    """
    Retorna os dados financeiros consolidados para o dashboard.
    Requer autenticação e um intervalo de datas.
    """
    # Chama a nova função do CRUD, passando o ID do usuário logado e as datas
    return crud.get_dashboard_data(
        db=db, 
        usuario_id=usuario_atual.id, 
        data_inicio=data_inicio, 
        data_fim=data_fim
    )

# --- ENDPOINTS DE CATEGORIAS ---

@app.post("/categorias/", response_model=schemas.Categoria)
def criar_nova_categoria(categoria: schemas.CategoriaCreate, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    """
    Endpoint para criar uma nova categoria. (Atualmente público)
    """
    return crud.criar_categoria(db=db, categoria=categoria)


@app.get("/categorias/", response_model=List[schemas.Categoria])
def ler_categorias(db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    """
    Endpoint para listar todas as categorias existentes. (Atualmente público)
    """
    categorias = crud.listar_categorias(db=db)
    return categorias


# --- ENDPOINT RAIZ ---

@app.get("/")
def ler_raiz():
    """
    Endpoint principal de boas-vindas.
    """
    return {"message": "Bem-vindo à API de Controle Financeiro!"}