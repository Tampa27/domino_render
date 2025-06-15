from celery import shared_task
from datetime import datetime
import logging
from dominoapp.utils.checktables import automatic_move_in_game
logger = logging.getLogger(__name__)

@shared_task
def automatic_move():
    hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[Celery] Hora actual: {hora_actual}")
    logger.info(f"[Celery] Hora actual: {hora_actual}")
    automatic_move_in_game()
    hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[Celery] Automatic Finish: {hora_actual}")
    logger.info(f"[Celery] Automatic Finish: {hora_actual}")
    return hora_actual