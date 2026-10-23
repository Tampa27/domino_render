import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')

app = Celery('domino')

# 1) Configuración de rendimiento y memoria
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
    task_always_eager=False,

    # Beat config
    beat_max_loop_interval=5,

    # Broker
    broker_pool_limit=5,
    broker_connection_retry_on_startup=True,

    # Serialization
    task_serializer='json',
    accept_content=['json'],
)

# 2) Cargar settings de Django (por si hay más configuración CELERY_*)
app.config_from_object('django.conf:settings', namespace='CELERY')

# 3) FORZAR broker desde la variable de entorno (prioridad sobre todo lo anterior)
_broker = os.environ.get('REDISCLOUD_URL') or os.environ.get('REDIS_URL')
if _broker:
    app.conf.broker_url = _broker
    app.conf.result_backend = _broker
    if _broker.startswith('rediss://'):
        app.conf.broker_use_ssl = {
            'ssl_cert_reqs': None,
            'ssl_check_hostname': False,
        }

app.autodiscover_tasks()