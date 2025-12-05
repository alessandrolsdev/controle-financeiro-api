# Arquivo: backend/tasks.py
"""Módulo de Tarefas Assíncronas (Celery Tasks).

Este módulo define as tarefas que serão executadas em segundo plano pelo
worker do Celery. Isso permite que operações pesadas ou não críticas para
a resposta imediata sejam processadas fora do ciclo de vida da requisição HTTP.

A principal tarefa atual é o recálculo de dados do dashboard após alterações.

Functions:
    task_recalculate_dashboard: Tarefa para recalcular métricas do dashboard em background.
"""

from datetime import date, timedelta

from backend.worker import celery_app
from backend.database import SessionLocal
from backend import crud

# --- TAREFA DE RECALCULAR O DASHBOARD ---

@celery_app.task(name="task_recalculate_dashboard")
def task_recalculate_dashboard(usuario_id: int):
    """Tarefa assíncrona para recalcular os dados do dashboard de um usuário.

    Esta função é executada por um worker Celery. Ela cria sua própria sessão
    de banco de dados, executa a lógica de cálculo do dashboard e (futuramente)
    pode atualizar um cache ou notificar o usuário.

    Args:
        usuario_id (int): O ID do usuário para o qual os dados devem ser recalculados.
    """
    print(f"[CELERY WORKER]: Recebida tarefa 'task_recalculate_dashboard' para usuario_id: {usuario_id}")
    
    db = SessionLocal()
    
    try:
        # Define o intervalo padrão de 30 dias para o cálculo
        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=30)

        # Executa a lógica de negócios pesada
        dashboard_data = crud.get_dashboard_data(
            db=db,
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        # Futuro: Atualizar Cache Redis ou enviar WebSocket
        
        print(f"[CELERY WORKER]: Tarefa concluída. Lucro líquido para usuario_id {usuario_id}: {dashboard_data.lucro_liquido}")

    except Exception as e:
        print(f"[CELERY WORKER]: ERRO na tarefa para usuario_id {usuario_id}. Erro: {e}")
    
    finally:
        db.close()
