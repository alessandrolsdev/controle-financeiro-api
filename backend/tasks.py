# Arquivo: backend/tasks.py (VERSÃO CORRIGIDA)
"""
O "Livro de Receitas" do nosso Worker Celery.

REATORAÇÃO (CORREÇÃO DE BUG):
1. Importamos a instância 'celery_app' do nosso 'worker.py'.
2. Mudamos o decorador de '@shared_task' (ambíguo)
   para '@celery_app.task' (explícito).

Isso FORÇA qualquer processo que importe esta tarefa (incluindo o
main.py da API) a usar a configuração do 'celery_app',
que aponta para o nosso "Carteiro" (Redis).
"""

# 1. MUDANÇA: Importamos 'shared_task'
# from celery import shared_task
# 1. CORREÇÃO: Importamos nossa app configurada do worker.py
from backend.worker import celery_app

from datetime import date, timedelta
from backend.database import SessionLocal
from backend import crud

# --- TAREFA DE RECALCULAR O DASHBOARD ---

# 2. MUDANÇA: @shared_task(name="task_recalculate_dashboard")
# 2. CORREÇÃO: Usamos o decorador da NOSSA app
@celery_app.task(name="task_recalculate_dashboard")
def task_recalculate_dashboard(usuario_id: int):
    """
    Uma tarefa assíncrona (Celery) que recalcula os dados do dashboard
    para um usuário específico.
    """
    print(f"[CELERY WORKER]: Recebida tarefa 'task_recalculate_dashboard' para usuario_id: {usuario_id}")
    
    db = SessionLocal()
    
    try:
        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=30)

        dashboard_data = crud.get_dashboard_data(
            db=db,
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        # --- ETAPA FUTURA (V2.2) ---
        # (Salvar em cache / Enviar via WebSocket)
        
        print(f"[CELERY WORKER]: Tarefa concluída. Lucro líquido para usuario_id {usuario_id}: {dashboard_data.lucro_liquido}")

    except Exception as e:
        print(f"[CELERY WORKER]: ERRO na tarefa para usuario_id {usuario_id}. Erro: {e}")
    
    finally:
        db.close()

