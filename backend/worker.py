# Arquivo: backend/worker.py
"""Módulo de Configuração do Worker Celery.

Este módulo configura a instância da aplicação Celery, define o broker de
mensagens (Redis) e registra as tarefas disponíveis. É o ponto de entrada
para o processo do worker.

O worker é responsável por executar tarefas assíncronas em segundo plano,
desacoplando o processamento pesado da API principal.

Attributes:
    celery_app (Celery): A instância da aplicação Celery configurada.
"""

from celery import Celery
from backend.core.config import settings

# Criação da instância Celery com a URL do broker (Redis)
celery_app = Celery(
    "backend",
    broker=settings.CELERY_BROKER_URL
)

# Configurações adicionais
celery_app.conf.update(
    timezone='America/Sao_Paulo', 
)

# Descobre automaticamente tarefas definidas no pacote 'backend' (ex: backend/tasks.py)
celery_app.autodiscover_tasks(
    packages=['backend']
)

@celery_app.task(name="test_ping")
def test_ping():
    """Tarefa de teste simples para verificar a saúde do worker.

    Returns:
        str: Retorna "Pong!" para confirmar a execução.
    """
    print(">>> PING-PONG (Celery Test Task) <<<")
    return "Pong!"
