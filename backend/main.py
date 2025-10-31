from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta, date

# Ajuste os imports para o seu projeto
from . import crud, models, schemas, security
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)
app = FastAPI()

origins = [
    "http://localhost:5173",
    # "https://seu-projeto-frontend.vercel.app", 
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

# --- ENDPOINTS ---

@app.post("/token", response_model=schemas.Token)
def login_para_obter_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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
    db_usuario = crud.get_usuario_por_nome(db, nome_usuario=usuario.nome_usuario)
    if db_usuario:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome de usuário já registrado")
    return crud.criar_usuario(db=db, usuario=usuario)

@app.get("/")
def ler_raiz():
    return {"message": "Bem-vindo à API de Controle Financeiro!"}

# --- ENDPOINTS PROTEGIDOS ---

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

@app.post("/transacoes/", response_model=schemas.Transacao)
def criar_nova_transacao(
    transacao: schemas.TransacaoCreate, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    return crud.criar_transacao(db=db, transacao=transacao, usuario_id=usuario_atual.id)

@app.get("/transacoes/", response_model=List[schemas.Transacao])
def ler_transacoes(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    transacoes = crud.listar_transacoes(db, usuario_id=usuario_atual.id, skip=skip, limit=limit)
    return transacoes

# <-- CORRIGIDO AQUI (Endpoint 1 de 2)
@app.post("/categorias/", response_model=schemas.Categoria)
def criar_nova_categoria(
    categoria: schemas.CategoriaCreate, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual) # Protege a rota
):
    """ Cria uma nova categoria GLOBAIL. (Protegido). """
    # Não passa 'usuario_id' pois categorias são globais
    return crud.criar_categoria(db=db, categoria=categoria)

# <-- CORRIGIDO AQUI (Endpoint 2 de 2)
@app.get("/categorias/", response_model=List[schemas.Categoria])
def ler_categorias(
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual) # Protege a rota
):
    """ Lista todas as categorias GLOBAIS. (Protegido). """
    # Não passa 'usuario_id'
    categorias = crud.listar_categorias(db=db)
    return categorias