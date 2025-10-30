# Arquivo: backend/main.py (Versão Completa e Final)

# --- 1. Importações ---
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta, date

# Importa todos os nossos módulos locais
from . import crud, models, schemas, security
from .database import SessionLocal, engine

# --- 2. Configuração Inicial ---

# Cria todas as tabelas no banco de dados (se não existirem)
models.Base.metadata.create_all(bind=engine)

# Inicia a aplicação FastAPI
app = FastAPI()

# --- 3. Configuração do CORS (O Porteiro) ---
# Define quais "bairros" (origens) podem falar com nossa API
origins = [
    "http://localhost:5173", # Nosso frontend em desenvolvimento
    "https://controle-financeiro-api-eight.vercel.app", # Nosso frontend em produção
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite todos os métodos (POST, GET, etc.)
    allow_headers=["*"], # Permite todos os cabeçalhos
)

# --- 4. Dependências de Segurança ---

# Define o esquema de segurança, apontando para o endpoint /token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    """Dependência para obter uma sessão do banco de dados."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Dependência de segurança ("O Segurança").
    Verifica o token e retorna o objeto do usuário atual.
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


# --- 5. ENDPOINTS (As "Portas" da API) ---

# --- Endpoints Públicos (Autenticação) ---

@app.post("/token", response_model=schemas.Token)
def login_para_obter_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Recebe username/password e retorna um Token JWT.
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
    Cria um novo usuário. (Público, para o primeiro registro).
    """
    db_usuario = crud.get_usuario_por_nome(db, nome_usuario=usuario.nome_usuario)
    if db_usuario:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome de usuário já registrado")
    
    return crud.criar_usuario(db=db, usuario=usuario)

@app.get("/")
def ler_raiz():
    """Endpoint principal de "Olá, Mundo"."""
    return {"message": "Bem-vindo à API de Controle Financeiro!"}


# --- Endpoints Protegidos (Requerem Login) ---

@app.get("/dashboard/", response_model=schemas.DashboardData)
def ler_dados_dashboard(
    data_inicio: date, 
    data_fim: date, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual) # < O "Segurança"
):
    """
    Retorna os dados financeiros consolidados para o dashboard.
    Requer autenticação.
    """
    return crud.get_dashboard_data(
        db=db, 
        usuario_id=usuario_atual.id, # Filtra dados pelo usuário logado
        data_inicio=data_inicio, 
        data_fim=data_fim
    )


@app.post("/transacoes/", response_model=schemas.Transacao)
def criar_nova_transacao(
    transacao: schemas.TransacaoCreate, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual) # < O "Segurança"
):
    """
    Cria uma nova transação (gasto ou receita) associada ao usuário logado.
    Requer autenticação.
    """
    return crud.criar_transacao(db=db, transacao=transacao, usuario_id=usuario_atual.id)


@app.get("/transacoes/", response_model=List[schemas.Transacao])
def ler_transacoes(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual) # < O "Segurança"
):
    """
    Lista as transações APENAS do usuário logado.
    Requer autenticação.
    """
    # Aqui usamos a versão SEGURA do crud.listar_transacoes que fizemos
    transacoes = crud.listar_transacoes(db, usuario_id=usuario_atual.id, skip=skip, limit=limit)
    return transacoes


@app.post("/categorias/", response_model=schemas.Categoria)
def criar_nova_categoria(
    categoria: schemas.CategoriaCreate, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual) # < O "Segurança"
):
    """
    Cria uma nova categoria. (Protegido).
    """
    return crud.criar_categoria(db=db, categoria=categoria)


@app.get("/categorias/", response_model=List[schemas.Categoria])
def ler_categorias(
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual) # < O "Segurança"
):
    """
    Lista todas as categorias. (Protegido).
    """
    categorias = crud.listar_categorias(db=db)
    return categorias