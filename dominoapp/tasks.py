from celery import shared_task
import logging
import os
from dominoapp.models import DominoGame, Tournament, Player, SummaryPlayer, Bank, Notification
from django.db import transaction
from django.db.models import F
from dominoapp.utils.transactions import create_game_transactions, create_transactions
from dominoapp.utils.players_tools import get_summary_model
from dominoapp.utils.move_register_utils import movement_register
from dominoapp.utils.checktables import procesar_logica_de_mesa, automatic_tournament
from dominoapp.utils.fcm_message import FCMNOTIFICATION
from dominoapp.utils.whatsapp_help import get_whatsapp_tournament_notify
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
                firts_bank = Bank.objects.first()
                update_kwargs = {k: F(k) + v for k, v in bank_update_data.items() if v != 0}
                if update_kwargs:
                    Bank.objects.filter(id=firts_bank.id).update(**update_kwargs)
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
                        create_game_transactions(
                            game= game,
                            to_user=player if trans.get('to_user') else None,
                            from_user=player if trans.get('from_user') else None,
                            amount=trans['amount'],
                            status="cp",
                            descriptions=trans['description'],
                            move_register=move_register
                        )
                    except:
                        create_transactions(
                            to_user=player if trans.get('to_user') else None,
                            from_user=player if trans.get('from_user') else None,
                            amount=trans['amount'],
                            status="cp",
                            type="gm",
                            descriptions=trans['description']
                        )
        except Exception as e:
            logger.error(f"Error procesando jugador {data.get('id')} en proceso asincrono: {e}")

@shared_task(name="async_update_player_presence", ignore_result=True)
def async_update_player_presence(player_data: dict):
    """
    Procesa actualizaciones de presencia de jugadores.
    """
    player_id = player_data.get('id')
    if not player_id:
        logger.error("Error: player_data debe contener 'id'.")
        return

    try:
        Player.objects.filter(id=player_id).update(**player_data)

    except Exception as e:
        logger.error(f"Error actualizando presencia del Jugador en proceso asincrono: {e}")

    return


@shared_task(name="async_send_fcm_message", ignore_result=True)
def async_send_fcm_message(users_id: list[int], title: str, message: str):
    """
    Procesa el envío de mensajes FCM a usuarios.
    """
    FCMNOTIFICATION.send_fcm_message_by_users_list(
        users = users_id,
        title = title,
        body = message
    )

    return

@shared_task(name="async_send_global_fcm_message", ignore_result=True)
def async_send_global_fcm_message(title: str, message: str):
    """
    Procesa el envío de mensajes FCM a todos los usuarios.
    """
    FCMNOTIFICATION.send_fcm_global_message(
        title = title,
        body = message
    )

    return

@shared_task(name="", ignore_result=True)
def async_save_place_tournament_notification(place_1_notification: dict, place_2_notification: dict, place_3_notification: dict):
    """
    Procesa las notificaciones de los lugares en un torneo.
    """ 
    admin_phone = os.environ.get('ADMIN_PHONE', None)
    if not admin_phone:
        admin_phone = "+5352459418"
        logger.critical("ADMIN_PHONE no está configurado en las variables de entorno.")

    if not place_1_notification:
        logger.error("Error: place_1_notification debe ser un diccionario.")
        return
    
    users_1er_place = place_1_notification.get('users_id')
    if not users_1er_place:
        logger.error("Error: place_1_notification debe contener 'users_id'.")
        return
    
    message_1er_place = place_1_notification.get("message")
    if message_1er_place:
        FCMNOTIFICATION.send_fcm_message_by_users_list(
            users = users_1er_place,
            title = place_1_notification.get('title'),
            body = message_1er_place
        )
    
    try:
        players_1er_place = Player.objects.filter(user__id__in = users_1er_place)
        for player in players_1er_place:            
            whatsapp_url = get_whatsapp_tournament_notify(
                player=player,
                player_phone=admin_phone,
                message=message_1er_place
            )

            Notification.objects.create(
                player=player,
                title=place_1_notification.get('title'),
                message=f"{message_1er_place}. Tienes 10 días para reclamar tu premio.",
                whatsapp_url = whatsapp_url
            )
    except Exception as error:
        logger.error(f"Error al crear las notificaciones del Torneo para el 1er lugar, error: {error}")

    if place_2_notification:
        users_2nd_place = place_2_notification.get('users_id')
        if users_2nd_place:
            message_2nd_place = place_2_notification.get("message")
            if message_2nd_place:
                FCMNOTIFICATION.send_fcm_message_by_users_list(
                    users = users_2nd_place,
                    title = place_2_notification.get('title'),
                    body = message_2nd_place
                )
            
            try:
                players_2nd_place = Player.objects.filter(user__id__in = users_2nd_place)
                for player in players_2nd_place:
                    whatsapp_url = get_whatsapp_tournament_notify(
                        player=player,
                        player_phone=admin_phone,
                        message=message_2nd_place
                    )

                    Notification.objects.create(
                        player= player,
                        title= place_2_notification.get('title'),
                        message=f"{message_2nd_place}. Tienes 10 días para reclamar tu premio.",
                        whatsapp_url = whatsapp_url
                    )
            except Exception as error:
                logger.error(f"Error al crear las notificaciones del Torneo para el 2do lugar, error: {error}")

    if place_3_notification:
        users_3th_place = place_3_notification.get('users_id')
        if users_3th_place:
            message_3th_place = place_3_notification.get("message")
            if message_3th_place:
                FCMNOTIFICATION.send_fcm_message_by_users_list(
                    users = users_3th_place,
                    title = place_3_notification.get('title'),
                    body = message_3th_place
                )
            
            try:
                players_3th_place = Player.objects.filter(user__id__in = users_3th_place)
                for player in players_3th_place:
                    whatsapp_url = get_whatsapp_tournament_notify(
                        player=player,
                        player_phone=admin_phone,
                        message=message_3th_place
                    )

                    Notification.objects.create(
                        player= player,
                        title= place_3_notification.get('title'),
                        message=f"{message_3th_place}. Tienes 10 días para reclamar tu premio.",
                        whatsapp_url = whatsapp_url
                    )
            except Exception as error:
                logger.error(f"Error al crear las notificaciones del Torneo para el 3er lugar, error: {error}")

    return