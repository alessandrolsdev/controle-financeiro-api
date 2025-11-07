# Arquivo: backend/worker.py (NOVO ARQUIVO)
"""
O Ponto de Entrada (Entrypoint) do nosso "Trabalhador" Celery.

Este arquivo é o "main.py" do Celery. Ele é responsável por:
1. Criar a instância da aplicação Celery.
2. Ler a configuração (a URL do Redis) do nosso 'core.config'.
3. Descobrir automaticamente quais tarefas existem (o 'tasks.py' que criaremos).

Para rodar este worker (em um terminal SEPARADO):
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
    # (Opcional: 'backend=settings.CELERY_RESULT_BACKEND')
)

# 2. Configuração do Celery
celery_app.conf.update(
    # Define o fuso horário para garantir que as tarefas agendadas
    # rodem no horário correto (importante para o Brasil).
    timezone='America/Sao_Paulo', 
    # (Podemos adicionar mais configurações aqui no futuro)
)

# 3. Auto-descoberta de Tarefas
# Diz ao Celery para procurar automaticamente por um arquivo chamado 'tasks.py'
# dentro de todos os 'INSTALLED_APPS' (que no nosso caso é o 'backend').
# Nós ainda não criamos este arquivo, mas vamos criar a seguir.
celery_app.autodiscover_tasks(
    packages=['backend']
)

# (Opcional) Uma tarefa de "ping" para testar se o worker está vivo
@celery_app.task(name="test_ping")
def test_ping():
    print(">>> PING-PONG (Celery Test Task) <<<")
    return "Pong!"