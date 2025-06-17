from celery import shared_task
import logging
from dominoapp.utils.checktables import automatic_move_in_game
logger = logging.getLogger(__name__)

@shared_task
def automatic_move():
    
    automatic_move_in_game()
    
    return