# Arquivo: backend/core/config.py (VERSÃO V-REVERTIDA COMPLETA)
"""
REVERSÃO (MISSÃO DE DEPLOY GRATUITO):
O Render não permite um DB e um Redis gratuitos.
Tornamos o 'CELERY_BROKER_URL' 100% opcional ('Optional[str] = None').
A API agora pode iniciar sem ele.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
# 1. IMPORTA 'Optional'
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
    
    # --- 2. CONFIGURAÇÃO DA FILA (AGORA OPCIONAL) ---
    CELERY_BROKER_URL: Optional[str] = None # <-- MUDANÇA CRÍTICA
    
    
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding='utf-8',
        extra='ignore' 
    )

settings = Settings()