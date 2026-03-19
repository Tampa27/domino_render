from celery import shared_task
import logging
from dominoapp.utils.checktables import automatic_move_in_game, automatic_tournament, automatic_exit_player
logger = logging.getLogger(__name__)

@shared_task(name="task_movimientos_juego")
def task_movimientos_juego():
    """Ejecuta solo la lógica de movimientos y jugadas automáticas."""
    automatic_move_in_game()

@shared_task(name="task_logica_torneos")
def task_logica_torneos():
    """Ejecuta la lógica de emparejamiento y premios de torneos."""
    automatic_tournament()

@shared_task(name="task_limpieza_jugadores")
def task_limpieza_jugadores():
    """Expulsa jugadores inactivos (puede ser menos frecuente)."""
    automatic_exit_player()