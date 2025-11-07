# Arquivo: backend/core/config.py (VERSÃO REATORADA)
"""
Módulo de Configuração Central - A "Fonte Única da Verdade".
REATORAÇÃO (Missão V2.1):
Adicionamos a 'CELERY_BROKER_URL' para que o FastAPI e o Worker
saibam como se conectar ao Redis (o "Carteiro" das tarefas).
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_PATH = os.path.join(ROOT_DIR, '.env')


class Settings(BaseSettings):
    """
    Classe que mapeia e valida as variáveis de ambiente.
    """
    
    # --- Configurações de Segurança ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # --- Configurações do Banco de Dados ---
    DATABASE_URL: Optional[str] = None
    
    # --- 1. NOVA CONFIGURAÇÃO DA FILA (CELERY) ---
    # O Pydantic vai procurar por 'CELERY_BROKER_URL' no .env,
    # mas se não achar, usará o valor padrão do Docker/localhost.
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    
    # (O Celery também pode usar um 'result_backend' para armazenar
    # resultados, mas para nossa tarefa de "dispare e esqueça",
    # o broker é o suficiente por enquanto.)
    
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding='utf-8',
        extra='ignore' 
    )

settings = Settings()