from celery import shared_task
import logging
from dominoapp.models import DominoGame, Tournament, Player, SummaryPlayer, Bank, MoveRegister
from django.db import transaction
from django.db.models import F
from dominoapp.utils.transactions import create_game_transactions
from dominoapp.utils.players_tools import get_summary_model
from dominoapp.utils.move_register_utils import movement_register
from dominoapp.utils.checktables import procesar_logica_de_mesa, automatic_tournament
logger = logging.getLogger('django')

@shared_task(name="task_maestra_domino", ignore_result=True)
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

@shared_task(name="procesar_mesa_individual", ignore_result=True)
def procesar_mesa_individual(game_id):
    """
    Procesa toda la lógica (movimientos, reinicios, expulsiones) de una sola mesa.
    """
    procesar_logica_de_mesa(game_id)


@shared_task(name="task_logica_torneos", ignore_result=True)
def task_logica_torneos(tournament_id):
    """Procesa toda la lógica de los torneos (reinicios, expulsiones, notificaciones)."""
    automatic_tournament(tournament_id)


@shared_task(name="async_update_summarys", ignore_result=True)
def async_update_summarys(game_id: int= None, player_data_list: list = None, bank_update_data: dict=None, move_data: dict = None):
    """
    Procesa actualizaciones masivas de estadísticas, transacciones y registros de movimientos.
    """
    # 1. Actualizar Banco
    if bank_update_data:
        try:
            with transaction.atomic():
                bank = Bank.objects.select_for_update().first() or Bank.objects.create()
                update_kwargs = {k: F(k) + v for k, v in bank_update_data.items() if v != 0}
                if update_kwargs:
                    Bank.objects.filter(id=bank.id).update(**update_kwargs)
        except Exception as e:
            logger.error(f"Error actualizando Banco en proceso asincrono: {e}")

    # 2. Registrar el Movimiento (Movido desde game_tools.py)
    move_register = None
    if move_data:
        try:
            move_register = movement_register(**move_data)
        except Exception as e:
            logger.error(f"Error creando MoveRegister en proceso asincrono: {e}")

    if not player_data_list:
        return

    # 3. Iterar sobre jugadores
    for data in player_data_list:
        try:
            with transaction.atomic():
                player = Player.objects.get(id=data['id'])
                
                # Actualizar Summary (Estadísticas acumuladas)
                if data.get('summary_fields'):
                    summary = get_summary_model(player)
                    summary_updates = {k: F(k) + v for k, v in data['summary_fields'].items()}
                    SummaryPlayer.objects.filter(id=summary.id).update(**summary_updates)

                # Crear Transacción
                trans = data.get('transaction')
                if trans:
                    try:
                        game = DominoGame.objects.get(id=game_id) if game_id else None
                    except DominoGame.DoesNotExist:
                        continue  # Si no existe el juego, saltamos la transacción
                    create_game_transactions(
                        game= game,
                        to_user=player if trans.get('to_user') else None,
                        from_user=player if trans.get('from_user') else None,
                        amount=trans['amount'],
                        status="cp",
                        descriptions=trans['description'],
                        move_register=move_register
                    )
        except Exception as e:
            logger.error(f"Error procesando jugador {data.get('id')} en proceso asincrono: {e}")
