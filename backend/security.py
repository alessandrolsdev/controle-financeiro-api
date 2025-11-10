# Arquivo: backend/security.py
"""
Módulo de Segurança - O "Cofre" do Projeto.

Este módulo isola toda a lógica de segurança crítica da aplicação.
Responsabilidades:
1. Hashing e verificação de senhas (usando Argon2).
2. Criação e verificação de Tokens de Acesso (JWT).

Ele é chamado pelo 'crud.py' (para criar usuários) e pelo 'main.py'
(para 'get_usuario_atual' e '/token').
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

# Importa os schemas para type hinting
from . import schemas
# Importa a 'settings' (nossa fonte única da verdade para 'SECRET_KEY')
from .core.config import settings


# --- 1. Configurações de Segurança ---
# (Lidas do 'settings', que por sua vez lê do .env)
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# --- 2. Contexto de Senha ---

# Decisão de Engenharia:
# Usamos 'argon2' como o esquema de hashing principal. É o padrão
# moderno recomendado pelo OWASP, mais forte que bcrypt ou PBKDF2.
# 'deprecated="auto"' atualiza hashes antigos se um dia mudarmos o esquema.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# --- 3. Funções de Senha ---

def verificar_senha(senha_plana: str, senha_hashed: str) -> bool:
    """
    Verifica se uma senha em texto plano (do formulário de login)
    corresponde a uma senha hasheada (do banco de dados).

    Args:
        senha_plana (str): A senha como o usuário a digitou (ex: "1234").
        senha_hashed (str): A senha como está salva no banco (ex: "$argon2id$v=19...").

    Returns:
        bool: True se as senhas correspondem, False caso contrário.
    """
    return pwd_context.verify(senha_plana, senha_hashed)

def get_hash_da_senha(senha: str) -> str:
    """
    Gera um hash seguro (Argon2) para uma senha em texto plano.

    Args:
        senha (str): A senha em texto plano (vinda do formulário de criação).

    Returns:
        str: O hash resultante, pronto para ser salvo no banco.
    """
    return pwd_context.hash(senha)


# --- 4. Funções de Token (JWT) ---

def criar_token_de_acesso(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um novo Token de Acesso (JWT) assinado.

    Args:
        data (dict): Os dados a serem codificados no "payload" (corpo) do token.
                     (Usamos {"sub": "nome_do_usuario"}).
        expires_delta (Optional[timedelta]): O tempo de vida customizado. Se None,
                                             usa o padrão de 'settings'.

    Returns:
        str: O token JWT assinado e codificado como uma string.
    """
    to_encode = data.copy()
    
    # Define o tempo de expiração
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Decisão de Engenharia: Usamos 'datetime.now(timezone.utc)'
        # para garantir que os tempos de expiração sejam independentes
        # do fuso horário do servidor.
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    
    # "Assina" o token usando nossa chave secreta e algoritmo
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verificar_token_de_acesso(token: str, credentials_exception: HTTPException) -> schemas.TokenData:
    """
    Decodifica e valida um Token de Acesso (JWT) vindo do usuário.
    Usado pela dependência 'get_usuario_atual' em main.py.

    Args:
        token (str): A string do token (vinda do header 'Authorization').
        credentials_exception (HTTPException): A exceção que deve ser
                                             levantada se a validação falhar.

    Raises:
        credentials_exception: Se o token for inválido, expirado ou malformado.

    Returns:
        schemas.TokenData: Um objeto Pydantic contendo os dados do token (o 'nome_usuario').
    """
    try:
        # Tenta decodificar o token usando a MESMA chave secreta
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extrai o nome de usuário (que salvamos no campo "sub" de "subject")
        nome_usuario: str = payload.get("sub")
        if nome_usuario is None:
            # Se o token não tiver um campo "sub", é inválido
            raise credentials_exception
        
        # Retorna os dados validados
        return schemas.TokenData(nome_usuario=nome_usuario)
    
    except JWTError:
        # Pega qualquer erro da biblioteca JWT (expirado, assinatura inválida, etc.)
        # e levanta nossa exceção padrão de "não autorizado".
        raise credentials_exception