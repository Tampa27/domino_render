import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
app = Celery('domino', broker=os.getenv('REDISCLOUD_URL', 'redis://localhost:6379/0'))
# Configuración de rendimiento y memoria.
app.conf.update(
    # --- Optimización de Workers ---
    worker_max_tasks_per_child=100,  # Reinicia workers cada 100 tareas (evita fugas de memoria).
    worker_max_memory_per_child=200000,  # 200 MB por worker (en KB).
    worker_concurrency=1,  # Número de hilos por worker (ajusta según CPU del dyno).
    worker_prefetch_multiplier=1,  # Solo toma 1 tarea a la vez.
    
    # --- Manejo de Tareas ---
    task_acks_late=True,  # Evita pérdida de tareas si el worker muere.
    task_reject_on_worker_lost=True,  # Reintenta tareas si hay un reinicio.
    task_time_limit=30,  # Mata tareas que excedan 30 segundos.
    task_soft_time_limit=25,  # Notifica a la tarea antes de matarla.
    
    # --- Redis (Broker) ---
    broker_pool_limit=10,  # Conexiones máximas al broker (evita sobrecarga).
    broker_connection_timeout=30,  # Timeout para conexiones.
    
    # --- Serialización ---
    task_serializer='json',  # Usa JSON (más ligero que pickle).
    result_serializer='json',
    accept_content=['json'],
)

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()