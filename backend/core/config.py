# Arquivo: backend/core/config.py
"""Módulo de Configuração Central da Aplicação.

Este módulo é responsável por carregar e validar todas as variáveis de ambiente
necessárias para a execução do backend. Utiliza o Pydantic Settings para garantir
que as configurações estejam tipadas e presentes.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Define o caminho absoluto para a pasta raiz do projeto
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_PATH = os.path.join(ROOT_DIR, '.env')


class Settings(BaseSettings):
    """Configurações globais da aplicação carregadas de variáveis de ambiente.

    Esta classe define o esquema de configuração, incluindo chaves de segurança,
    conexão com banco de dados e configurações de filas de tarefas.

    Attributes:
        SECRET_KEY (str): Chave secreta usada para assinar tokens JWT e outras operações criptográficas.
        ALGORITHM (str): Algoritmo de criptografia usado para gerar tokens JWT. Padrão: "HS256".
        ACCESS_TOKEN_EXPIRE_MINUTES (int): Tempo de expiração dos tokens de acesso em minutos. Padrão: 30.
        DATABASE_URL (Optional[str]): URL de conexão com o banco de dados. Se não fornecido, pode-se usar um fallback (e.g., SQLite).
        CELERY_BROKER_URL (Optional[str]): URL do broker de mensagens para o Celery (ex: Redis). Opcional para deploys que não utilizam filas.
    """
    
    # --- Configurações de Segurança ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # --- Configurações do Banco de Dados ---
    DATABASE_URL: Optional[str] = None
    
    # --- Configurações da Fila ---
    CELERY_BROKER_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding='utf-8',
        extra='ignore' 
    )

# Cria uma instância única das configurações.
settings = Settings()
