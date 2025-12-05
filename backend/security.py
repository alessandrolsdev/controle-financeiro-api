# Arquivo: backend/security.py
"""Módulo de Segurança e Autenticação.

Este módulo implementa as funções críticas de segurança da aplicação, incluindo
hashing de senhas e gerenciamento de tokens JWT (JSON Web Tokens).

Utiliza a biblioteca Passlib com Argon2 para hashing de senhas e a biblioteca
Python-Jose para codificação e decodificação de tokens JWT.

Functions:
    verificar_senha: Confere se uma senha em texto plano corresponde a um hash.
    get_hash_da_senha: Gera o hash seguro de uma senha.
    criar_token_de_acesso: Gera um token JWT assinado.
    verificar_token_de_acesso: Valida e decodifica um token JWT.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from . import schemas
from .core.config import settings

# --- Configurações de Segurança ---
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# --- Contexto de Senha ---

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# --- Funções de Senha ---

def verificar_senha(senha_plana: str, senha_hashed: str) -> bool:
    """Verifica se a senha fornecida corresponde ao hash armazenado.

    Args:
        senha_plana (str): A senha em texto plano fornecida pelo usuário.
        senha_hashed (str): O hash da senha armazenado no banco de dados.

    Returns:
        bool: True se as senhas conferem, False caso contrário.
    """
    return pwd_context.verify(senha_plana, senha_hashed)

def get_hash_da_senha(senha: str) -> str:
    """Gera um hash seguro para a senha fornecida usando Argon2.

    Args:
        senha (str): A senha em texto plano.

    Returns:
        str: O hash da senha gerado.
    """
    return pwd_context.hash(senha)


# --- Funções de Token (JWT) ---

def criar_token_de_acesso(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um token de acesso JWT com tempo de expiração.

    Args:
        data (dict): Dicionário com os dados (claims) a serem incluídos no token.
        expires_delta (Optional[timedelta]): Tempo de expiração personalizado. Se None, usa o padrão.

    Returns:
        str: O token JWT codificado.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verificar_token_de_acesso(token: str, credentials_exception: HTTPException) -> schemas.TokenData:
    """Valida um token de acesso JWT e extrai as informações do usuário.

    Args:
        token (str): O token JWT a ser validado.
        credentials_exception (HTTPException): Exceção a ser lançada em caso de falha na validação.

    Raises:
        credentials_exception: Se o token for inválido, expirado ou não contiver o nome de usuário.

    Returns:
        schemas.TokenData: Objeto contendo os dados extraídos do token (ex: nome de usuário).
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        nome_usuario: str = payload.get("sub")
        if nome_usuario is None:
            raise credentials_exception
        
        return schemas.TokenData(nome_usuario=nome_usuario)
    
    except JWTError:
        raise credentials_exception
