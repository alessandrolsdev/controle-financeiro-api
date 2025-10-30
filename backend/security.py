# Arquivo: backend/security.py (Versão Completa e Corrigida)

from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt

from . import schemas # <-- Esta importação é crucial para a nova função!

# --- Configuração do Token JWT ---
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- Contexto de Senha ---
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# --- Funções de Senha ---
def verificar_senha(senha_plana: str, senha_hashed: str) -> bool:
    return pwd_context.verify(senha_plana, senha_hashed)

def get_hash_da_senha(senha: str) -> str:
    return pwd_context.hash(senha)

# --- Funções de Token JWT ---
def criar_token_de_acesso(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- ESTA É A FUNÇÃO QUE ESTAVA FALTANDO ---
def verificar_token_de_acesso(token: str, credentials_exception):
    """
    Decodifica um token JWT e extrai o nome de usuário.
    """
    try:
        # Tenta decodificar o token usando nossa chave secreta e algoritmo.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Extrai o nome de usuário do campo "sub" (subject).
        nome_usuario: str = payload.get("sub")
        if nome_usuario is None:
            # Se não houver nome de usuário, lança uma exceção.
            raise credentials_exception
        # Retorna os dados do token.
        return schemas.TokenData(nome_usuario=nome_usuario)
    except JWTError:
        # Se o token for inválido ou expirado, lança a exceção.
        raise credentials_exception