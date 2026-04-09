import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
app = Celery('domino')
# Configuración de rendimiento y memoria.
app.conf.update(
    timezone='UTC',
    enable_utc=True,
    
    # Worker config
    worker_max_tasks_per_child=100,
    worker_max_memory_per_child=200000,
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    
    # Task config
    task_acks_late=False,
    task_reject_on_worker_lost=True,
    task_time_limit=30,
    task_soft_time_limit=25,
    task_track_started=True,
    
    # Beat config - importante para que funcione con --beat
    beat_max_loop_interval=5,  # Revisar tareas cada 5 segundos
    
    # Broker
    broker_pool_limit=10,
    broker_connection_retry_on_startup=True,
    
    # Serialization
    task_serializer='json',
    accept_content=['json'],
)

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()