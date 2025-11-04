# Arquivo: backend/security.py
# Responsabilidade: O "Cofre" do nosso projeto.
# Gerencia toda a lógica de segurança crítica:
# 1. Hashing e verificação de senhas (usando Argon2).
# 2. Criação e verificação de Tokens de Acesso (JWT).

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status # Importação para tipagem
from dotenv import load_dotenv

# Importa os schemas para type hinting
from . import schemas

# --- 1. Carregamento das Variáveis de Ambiente ---

# Carrega as variáveis do arquivo .env (que está na raiz do projeto, não aqui)
# A pasta raiz é 'controle-financeiro-api/'
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)


# --- 2. Configurações de Segurança ---

# CHAVE SECRETA (LIDA DO .ENV)
# Esta é a chave "mestra" usada para assinar nossos tokens.
# NUNCA deve ser escrita diretamente no código.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Trava de segurança para impedir que o app rode sem a chave
    raise RuntimeError("FALHA CRÍTICA: SECRET_KEY não foi definida no arquivo .env")

ALGORITHM = "HS256" # Algoritmo de assinatura do JWT
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Tempo de vida de um token de login

# --- 3. Contexto de Senha ---

# Define o algoritmo de hashing. Usamos Argon2, o padrão moderno e seguro.
# 'deprecated="auto"' atualiza hashes antigos se um dia mudarmos o algoritmo.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# --- 4. Funções de Senha ---

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
    Gera um hash seguro para uma senha em texto plano.

    Args:
        senha (str): A senha em texto plano (vinda do formulário de criação).

    Returns:
        str: O hash Argon2 resultante, pronto para ser salvo no banco.
    """
    return pwd_context.hash(senha)


# --- 5. Funções de Token (JWT) ---

def criar_token_de_acesso(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um novo Token de Acesso (JWT).

    Args:
        data (dict): Os dados a serem codificados no "payload" (corpo) do token.
                     (Ex: {"sub": "nome_do_usuario"})
        expires_delta (Optional[timedelta]): O tempo de vida customizado. Se None,
                                           usa o padrão de 30 minutos.

    Returns:
        str: O token JWT assinado e codificado como uma string.
    """
    to_encode = data.copy()
    
    # Define o tempo de expiração
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # "Assina" o token usando nossa chave secreta
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verificar_token_de_acesso(token: str, credentials_exception: HTTPException) -> schemas.TokenData:
    """
    Decodifica e valida um Token de Acesso (JWT) vindo do usuário.
    Usado pelo "segurança" (get_usuario_atual) em main.py.

    Args:
        token (str): A string do token (vinda do cabeçalho 'Authorization').
        credentials_exception (HTTPException): A exceção que deve ser
                                             levantada se a validação falhar.

    Raises:
        credentials_exception: Se o token for inválido, expirado ou malformado.

    Returns:
        schemas.TokenData: Um objeto Pydantic contendo os dados do token (o nome de usuário).
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