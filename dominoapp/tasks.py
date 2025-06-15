from celery import shared_task
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

@shared_task
def mostrar_hora():
    hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[Celery] Hora actual: {hora_actual}")
    logger.info(f"[Celery] Hora actual: {hora_actual}")
    return hora_actual