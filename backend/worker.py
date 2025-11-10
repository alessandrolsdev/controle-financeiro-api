# Arquivo: backend/worker.py
"""
Ponto de Entrada (Entrypoint) do "Trabalhador" Celery.

Este arquivo é o "main.py" do Celery. Ele é responsável por:
1. Criar a instância da aplicação Celery.
2. Ler a configuração (a 'CELERY_BROKER_URL' do Redis) do 'core.config'.
3. Descobrir automaticamente (autodiscover) as tarefas definidas em 'tasks.py'.

Este arquivo NÃO é usado pelo Uvicorn (API). Ele é chamado
diretamente pelo comando do Celery no terminal de desenvolvimento.

Comando para iniciar (no Terminal 2):
celery -A backend.worker.celery_app worker --loglevel=info
"""

from celery import Celery

# Importa nossas configurações centrais
from backend.core.config import settings

# 1. Cria a instância do Celery
# O primeiro argumento 'backend' é o nome do módulo principal.
# O 'broker' é a URL do nosso "Carteiro" (Redis), lida do 'settings'.
celery_app = Celery(
    "backend",
    broker=settings.CELERY_BROKER_URL
    # (O 'result_backend' não é necessário para nossas tarefas
    #  de "dispare e esqueça" (fire-and-forget)).
)

# 2. Configuração do Celery
celery_app.conf.update(
    # Define o fuso horário para garantir que as tarefas agendadas
    # rodem no horário correto (importante para o Brasil).
    timezone='America/Sao_Paulo', 
)

# 3. Auto-descoberta de Tarefas
# Diz ao Celery para procurar automaticamente por um arquivo chamado 'tasks.py'
# dentro dos pacotes listados (no nosso caso, 'backend').
celery_app.autodiscover_tasks(
    packages=['backend']
)

# (Opcional) Uma tarefa de "ping" para testar se o worker está vivo
@celery_app.task(name="test_ping")
def test_ping():
    """Tarefa de teste para verificar a conexão do worker."""
    print(">>> PING-PONG (Celery Test Task) <<<")
    return "Pong!"