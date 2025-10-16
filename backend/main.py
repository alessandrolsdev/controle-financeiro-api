# Arquivo: backend/main.py (versão final com endpoint protegido)

# --- Importações ---
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta

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
    token_data = security.verificar_token_de_acesso(token, credentials_exception)
    usuario = crud.get_usuario_por_nome(db, nome_usuario=token_data.nome_usuario)
    if usuario is None:
        raise credentials_exception
    return usuario


# --- ENDPOINTS ---

@app.post("/token", response_model=schemas.Token)
def login_para_obter_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # ... (código do login existente, sem alterações)
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

# --- Endpoint de Transações (AGORA PROTEGIDO) ---
@app.post("/transacoes/", response_model=schemas.Transacao)
def criar_nova_transacao(transacao: schemas.TransacaoCreate, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    """
    Cria uma nova transação. Requer autenticação.
    O ID do usuário é pego automaticamente do token de acesso.
    """
    return crud.criar_transacao(db=db, transacao=transacao, usuario_id=usuario_atual.id)


# --- Outros Endpoints (ainda públicos) ---

@app.get("/")
def ler_raiz():
    return {"message": "Bem-vindo à API de Controle Financeiro!"}

# ... (o resto dos endpoints de usuários e categorias continua aqui) ...