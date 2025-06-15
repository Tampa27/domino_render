import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
app = Celery('domino', broker=os.getenv('REDISCLOUD_URL', 'redis://localhost:6379/0'))
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()