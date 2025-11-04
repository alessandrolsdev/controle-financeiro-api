# Arquivo: backend/main.py (VERSÃO FINAL DOCUMENTADA)
# Responsabilidade: O "Controlador" (Controller) da nossa arquitetura.
# Define todos os endpoints (rotas) da API, lida com a segurança
# e delega a lógica de negócios para o 'crud.py'.

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

# Esta linha é crucial: ela diz ao SQLAlchemy para olhar o 'models.py'
# e criar todas as tabelas (Usuario, Categoria, Transacao) no
# banco de dados (PostgreSQL no Render, SQLite localmente) se elas não existirem.
models.Base.metadata.create_all(bind=engine)

# Cria a instância principal da aplicação FastAPI
app = FastAPI()

# --- 3. Configuração do CORS (O "Porteiro") ---

# Define quais "bairros" (origens) da web têm permissão para "falar" com nossa API.
# Isso é uma medida de segurança fundamental.
origins = [
    "http://localhost:5173", # Nosso frontend em desenvolvimento (npm run dev)
    "http://localhost:4173", # Nosso frontend em preview (npm run preview)
    "https://controle-financeiro-api-eight.vercel.app", # Nosso frontend em produção no Vercel
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Permite apenas as origens na lista acima
    allow_credentials=True, # Permite que o frontend envie o token de login
    allow_methods=["*"], # Permite todos os métodos (GET, POST, PUT, DELETE)
    allow_headers=["*"], # Permite todos os cabeçalhos (incluindo 'Authorization')
)

# --- 4. Dependências de Segurança ---

# Define o "esquema" de segurança.
# Ele diz ao FastAPI: "Quando eu pedir, procure por um token no cabeçalho
# 'Authorization: Bearer ...' e o tokenUrl='/token' é onde o usuário o obtém."
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    """
    Dependência (Dependency) do FastAPI.
    Esta função gerencia a sessão do banco de dados para cada requisição.
    
    Ela usa 'yield' para:
    1. Criar e 'entregar' uma sessão (db) para o endpoint.
    2. 'Esperar' o endpoint terminar seu trabalho.
    3. Garantir que a sessão (db.close()) seja fechada, mesmo se um erro acontecer.
    Isso previne vazamento de conexões do banco.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Dependência de segurança ("O Segurança").
    Este é o "guarda" que colocamos na porta dos endpoints protegidos.

    1. Exige um token (via 'oauth2_scheme').
    2. Chama o 'security.py' para validar o token.
    3. Busca o usuário no banco de dados com base no token.
    4. Retorna o objeto 'models.Usuario' completo.

    Se qualquer etapa falhar (token inválido, usuário não encontrado),
    ela lança um erro HTTP 401, bloqueando o acesso.
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
    # O objeto 'usuario' é injetado no endpoint
    return usuario


# --- 5. ENDPOINTS (As "Portas" da API) ---

# --- Endpoints Públicos (Autenticação) ---

@app.post("/token", response_model=schemas.Token)
def login_para_obter_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    Endpoint de Login.
    Usa o 'OAuth2PasswordRequestForm' (padrão do FastAPI) para receber 
    'username' e 'password' de um formulário.
    Verifica as credenciais e retorna um Token JWT.
    """
    usuario = crud.get_usuario_por_nome(db, nome_usuario=form_data.username)
    # Verifica se o usuário existe E se a senha bate com o hash no banco
    if not usuario or not security.verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Cria o token com o tempo de expiração definido em 'security.py'
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.criar_token_de_acesso(
        data={"sub": usuario.nome_usuario}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/usuarios/", response_model=schemas.Usuario)
def criar_novo_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    """
    Endpoint público para criar um novo usuário (o primeiro registro).
    """
    # Verifica se o nome de usuário já está em uso
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
    Este endpoint é protegido: só funciona se um token válido for enviado.
    """
    return crud.get_dashboard_data(
        db=db, 
        usuario_id=usuario_atual.id, # Filtra dados pelo ID do usuário logado
        data_inicio=data_inicio, 
        data_fim=data_fim
    )


@app.post("/transacoes/", response_model=schemas.DashboardData)
def criar_nova_transacao(
    transacao: schemas.TransacaoCreate, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual) # < O "Segurança"
):
    """
    Cria uma nova transação (gasto ou receita) associada ao usuário logado.
    Requer autenticação.
    
    [Otimização de Engenharia]:
    Para evitar bugs de "condição de corrida" e cache, este endpoint
    salva a transação E, na mesma sessão, recalcula e retorna
    os dados do dashboard atualizados.
    """
    # 1. Salva a nova transação
    crud.criar_transacao(db=db, transacao=transacao, usuario_id=usuario_atual.id)
    
    # 2. Busca os dados do dashboard (na mesma sessão!)
    #    (Assumimos a mesma janela de 30 dias do frontend)
    data_fim = date.today()
    data_inicio = data_fim - timedelta(days=30)
    
    # 3. Retorna os dados do dashboard atualizados
    return crud.get_dashboard_data(
        db=db, 
        usuario_id=usuario_atual.id,
        data_inicio=data_inicio, 
        data_fim=data_fim
    )


@app.get("/transacoes/", response_model=List[schemas.Transacao])
def ler_transacoes(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual) # < O "Segurança"
):
    """
    Lista as transações (com paginação) APENAS do usuário logado.
    Requer autenticação.
    """
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