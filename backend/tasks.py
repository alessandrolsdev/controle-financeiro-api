# Arquivo: backend/tasks.py
"""
Módulo de Tarefas (Tasks) - O "Livro de Receitas" do Worker.

Este arquivo define todas as funções (tarefas) que queremos
executar em segundo plano (em background) via Celery.

O 'worker.py' (através do 'autodiscover_tasks') irá
encontrar e registrar automaticamente qualquer tarefa definida aqui.

Decisão de Arquitetura (V9.3 - Correção de Bug):
Usamos '@celery_app.task' (vinculado ao nosso 'worker.py') em vez
de '@shared_task' (agnóstico). Isso força qualquer processo que
importe esta tarefa (incluindo o 'main.py' no modo de dev assíncrono)
a usar a configuração correta do broker (Redis).
"""

from datetime import date, timedelta

# Importa a instância 'celery_app' configurada do 'worker.py'
from backend.worker import celery_app
# Importa a "fábrica" de sessões do nosso database.py
from backend.database import SessionLocal
# Importa o módulo 'crud' para reutilizar nossa lógica de negócios
from backend import crud

# --- TAREFA DE RECALCULAR O DASHBOARD ---

@celery_app.task(name="task_recalculate_dashboard")
def task_recalculate_dashboard(usuario_id: int):
    """
    Uma tarefa assíncrona (Celery) que recalcula os dados do dashboard
    para um usuário específico.

    Esta tarefa é chamada (via .delay()) pelos endpoints de
    criação, edição ou exclusão quando o modo assíncrono está ativo.
    
    Decisão de Engenharia (Gerenciamento de Sessão):
    Como o Celery é um processo totalmente separado, ele NÃO PODE
    usar as dependências (Depends(get_db)) do FastAPI.
    A tarefa DEVE criar e fechar sua própria sessão de
    banco de dados usando 'SessionLocal()' em um 'try/finally'.

    Args:
        usuario_id (int): O ID do usuário para o qual o dashboard
                          deve ser recalculado.
    """
    print(f"[CELERY WORKER]: Recebida tarefa 'task_recalculate_dashboard' para usuario_id: {usuario_id}")
    
    db = SessionLocal()
    
    try:
        # 1. Define o intervalo de datas (padrão de 30 dias)
        # (Nota: Em uma V3.0, idealmente o frontend enviaria
        #  o 'data_inicio' e 'data_fim' atuais para esta tarefa)
        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=30)

        # 2. CHAMA A LÓGICA DE NEGÓCIOS (A query "lenta")
        dashboard_data = crud.get_dashboard_data(
            db=db,
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        # --- ETAPA FUTURA (V8.0+) ---
        # É AQUI que, no futuro, nós iremos:
        # 1. Salvar 'dashboard_data' em um cache (Redis).
        # 2. Ou enviar 'dashboard_data' para o frontend
        #    via WebSocket para uma atualização em tempo real.
        
        print(f"[CELERY WORKER]: Tarefa concluída. Lucro líquido para usuario_id {usuario_id}: {dashboard_data.lucro_liquido}")

    except Exception as e:
        # Se a tarefa falhar, logamos o erro.
        # (Em produção, usaríamos um sistema de 'retry' do Celery)
        print(f"[CELERY WORKER]: ERRO na tarefa para usuario_id {usuario_id}. Erro: {e}")
    
    finally:
        # GARANTE que a sessão do banco de dados seja fechada,
        # não importa o que aconteça (sucesso ou falha).
        db.close()