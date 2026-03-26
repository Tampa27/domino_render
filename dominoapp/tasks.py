from celery import shared_task
import logging
from dominoapp.models import DominoGame, Tournament
from dominoapp.utils.checktables import procesar_logica_de_mesa, automatic_tournament
logger = logging.getLogger(__name__)

@shared_task(name="task_maestra_domino")
def task_maestra_domino():
    """
    Se ejecuta cada 7s. Identifica mesas activas y lanza procesos individuales.
    """
    # Filtramos mesas que no estén vacías y tengan estados que requieran atención
    # Estados: 'ru' (jugando), 'fg'/'fi' (terminado), 'wt'/'ready' (esperando)
    mesas_activas = DominoGame.objects.filter(
        player1__isnull=False,
        status__in=['ru', 'fg', 'fi', 'wt', 'ready']
    ).values_list('id', flat=True)

    for game_id in mesas_activas:
        # Lanzamos la subtarea para cada mesa de forma asíncrona
        procesar_mesa_individual.delay(game_id)
    
    # También lanzamos la lógica de torneos
    tournaments_active = Tournament.objects.filter(active=True).values_list('id', flat=True)
    for tournament_id in tournaments_active:
        task_logica_torneos.delay(tournament_id)

@shared_task(name="procesar_mesa_individual")
def procesar_mesa_individual(game_id):
    """
    Procesa toda la lógica (movimientos, reinicios, expulsiones) de una sola mesa.
    """
    procesar_logica_de_mesa(game_id)


@shared_task(name="task_logica_torneos")
def task_logica_torneos(tournament_id):
    """Procesa toda la lógica de los torneos (reinicios, expulsiones, notificaciones)."""
    automatic_tournament(tournament_id)

