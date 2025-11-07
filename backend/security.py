# Arquivo: backend/security.py (VERSÃO REATORADA)
# Responsabilidade: O "Cofre" do nosso projeto.
#
# REATORAÇÃO:
# Removemos TODA a lógica de 'os', 'load_dotenv' e 'getenv'.
# Removemos a checagem manual 'if not SECRET_KEY'.
# Agora, importamos as constantes validadas do 'settings'.

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException # 'status' não era usado diretamente aqui

# Importa os schemas para type hinting
from . import schemas

# --- 1. IMPORTAÇÃO DA CONFIGURAÇÃO CENTRAL ---
from .core.config import settings


# --- 2. Configurações de Segurança (Lidas do 'settings') ---

# A lógica de 'SECRET_KEY', 'ALGORITHM', e 'EXPIRE_MINUTES'
# foi movida para 'backend/core/config.py'.
# Nós apenas consumimos as variáveis validadas.
# O Pydantic já garantiu que 'SECRET_KEY' existe.


# --- 3. Contexto de Senha ---

# Define o algoritmo de hashing. Usamos Argon2, o padrão moderno e seguro.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# --- 4. Funções de Senha ---

def verificar_senha(senha_plana: str, senha_hashed: str) -> bool:
    """
    Verifica se uma senha em texto plano (do formulário de login)
    corresponde a uma senha hasheada (do banco de dados).
    """
    return pwd_context.verify(senha_plana, senha_hashed)

def get_hash_da_senha(senha: str) -> str:
    """
    Gera um hash seguro para uma senha em texto plano.
    """
    return pwd_context.hash(senha)


# --- 5. Funções de Token (JWT) ---

def criar_token_de_acesso(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um novo Token de Acesso (JWT).
    """
    to_encode = data.copy()
    
    # Define o tempo de expiração
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Lê o tempo de expiração do objeto 'settings'
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    
    # "Assina" o token usando nossa chave secreta e algoritmo do 'settings'
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def verificar_token_de_acesso(token: str, credentials_exception: HTTPException) -> schemas.TokenData:
    """
    Decodifica e valida um Token de Acesso (JWT) vindo do usuário.
    """
    try:
        # Tenta decodificar o token usando a chave e algoritmo do 'settings'
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        nome_usuario: str = payload.get("sub")
        if nome_usuario is None:
            raise credentials_exception
        
        return schemas.TokenData(nome_usuario=nome_usuario)
    
    except JWTError:
        raise credentials_exception