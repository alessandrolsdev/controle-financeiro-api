# Arquivo: backend/core/config.py
"""
Módulo de Configuração Central - A "Fonte Única da Verdade".

Este módulo usa o Pydantic `BaseSettings` (da biblioteca 'pydantic-settings')
para carregar e validar TODAS as variáveis de ambiente (do arquivo .env)
em um único lugar.

Isso previne a duplicação de lógica `load_dotenv` em outros arquivos
e garante que a aplicação falhe rapidamente (fail-fast) se uma
configuração crítica (como a SECRET_KEY) estiver faltando.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Define o caminho absoluto para a pasta raiz do projeto
# (um nível acima de 'backend', onde o .env está)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_PATH = os.path.join(ROOT_DIR, '.env')


class Settings(BaseSettings):
    """
    Classe que mapeia e valida as variáveis de ambiente.
    
    O Pydantic lê automaticamente os nomes (sem case-sensitive)
    das variáveis de ambiente do sistema ou do arquivo .env especificado.
    """
    
    # --- Configurações de Segurança (usadas por security.py) ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # --- Configurações do Banco de Dados (usadas por database.py) ---
    # É 'Optional' para permitir o fallback para o SQLite
    # se a DATABASE_URL não for definida no .env (modo de dev).
    DATABASE_URL: Optional[str] = None
    
    # --- Configurações da Fila (usadas pelo main.py / worker.py) ---
    # É 'Optional' para permitir que a API síncrona (deploy gratuito)
    # rode sem a necessidade de um broker Redis.
    CELERY_BROKER_URL: Optional[str] = None

    # Configuração do Pydantic para ler o arquivo .env
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding='utf-8',
        # 'extra="ignore"' impede que o Pydantic reclame de variáveis
        # extras no .env (como VITE_API_BASE_URL)
        extra='ignore' 
    )

# Cria uma instância única das configurações que será
# importada por todos os outros módulos do backend.
settings = Settings()