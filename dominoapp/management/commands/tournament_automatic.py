import os
import pytz
from django.core.management.base import BaseCommand
from django.db.models import F, Count, Value
from django.db.models.functions import Coalesce
from django.utils.timezone import timedelta
from django.utils import timezone
from dominoapp.models import Tournament, Player
from dominoapp.tasks import async_send_fcm_message, async_send_global_fcm_message
from dominoapp.utils.async_task_helper import safe_async_task
from dominoapp.utils.constants import TournamentStatus
import logging
logger = logging.getLogger("django")


class Command(BaseCommand):
    help = "Check the tournaments that are active and check the number of players and send some notifications to the players."

    def handle(self, *args, **options):
        tournaments = Tournament.objects.filter(active=True).prefetch_related(
            'player_list__user'           # Para notificaciones a todos los inscritos
        )
        now = timezone.now()
        current_hour = now.hour
        current_minute = now.minute
        tournament_notify_hour = os.getenv("TOURNAMENT_NOTIFY_HOURS", None)
        try:
            target_hour = int(tournament_notify_hour)
        except (TypeError, ValueError):
            target_hour = None
        if not target_hour:
            logger.critical(f"No se ha configurado el TOURNAMENT_NOTIFY_HOURS en las variables de entorno.")
        for tournament in tournaments:
            # analizar si el numero de player es par            
            player_list = tournament.player_list.all()
            player_in_tournament = player_list.count()
            ### Correr el torneo 1 dia por falta de jugadores
            if (
                (tournament.deadline < now < tournament.start_at and 
                player_in_tournament%2 != 0 and 
                int(player_in_tournament) < int(tournament.max_player)) or
                (tournament.deadline < now < tournament.start_at and 
                int(player_in_tournament) < int(tournament.min_player))
                ):
                tournament.deadline += timedelta(days=1)
                tournament.start_at += timedelta(days=1)
                tournament.save(update_fields=['deadline', 'start_at'])
                timezone_list = player_list.order_by("timezone").distinct("timezone").values_list("timezone", flat=True)
                for player_timezone in timezone_list:
                    players_id = player_list.filter(timezone=player_timezone).values_list("user__id", flat=True)
                    try:                        
                        safe_async_task(
                            async_send_fcm_message,
                            list(players_id), 
                            "⏰ Fechas del Torneo Corridas",
                            f"El torneo se pospuso para el {tournament.start_at.astimezone(pytz.timezone(player_timezone)).strftime('%d-%m-%Y, %H:%M')} debido a inscripciones incompletas. Las inscripciones siguen abiertas hasta el {tournament.deadline.astimezone(pytz.timezone(player_timezone)).strftime('%d-%m-%Y, %H:%M')}."
                        )
                    except Exception as error:
                            logger.error(f'Error al enviar notificacion FCM de cambio de fecha del torneo" => {str(error)}')
                
                try:
                    safe_async_task(
                        async_send_global_fcm_message,
                        "⏰ Última oportunidad para inscribirte al torneo",
                        f"⏰ Se corrió el torneo. Ahora puedes unirte al torneo antes del {tournament.deadline.astimezone(pytz.timezone('America/Havana')).strftime('%d-%m a las %H:%M')}."
                    )
                except Exception as error:
                    logger.error(f'Error al enviar notificacion FCM global de cambio de fecha del torneo" => {str(error)}')
            
            ### Recordatorio de cierre de inscripciones 12 horas antes del cierre de inscripciones
            diff_deadline = tournament.deadline - timedelta(hours=12)
            if (
                diff_deadline < now and not tournament.notification_deadline and
                player_in_tournament < int(tournament.max_player)
                ):
                try:
                    safe_async_task(
                        async_send_global_fcm_message,
                        "⏰ Últimas horas para inscribirte al torneo",
                        f"⏰ Inscripciones a punto de cerrar. Únete al torneo antes del {tournament.deadline.astimezone(pytz.timezone('America/Havana')).strftime('%d-%m a las %H:%M')}."
                    )
                except Exception as error:
                        logger.error(f'Error al enviar notificacion FCM global de recordatorio de cierre de inscripciones" => {str(error)}')
                
                tournament.notification_deadline = True
                tournament.save(update_fields=['notification_deadline'])

            ### Recordatorio de inicio 2 horas antes
            diff_start = tournament.start_at - timedelta(hours=2)
            if  diff_start < now and not tournament.notification_1 and int(player_in_tournament) == int(tournament.max_player):
                timezone_list = player_list.order_by("timezone").distinct("timezone").values_list("timezone", flat=True)
                for player_timezone in timezone_list:
                    players_id = player_list.filter(timezone=player_timezone).values_list("user__id", flat=True)
                    try:
                        safe_async_task(
                            async_send_fcm_message,
                            list(players_id),
                            "⏰ Recordatorio de inicio",
                            f"Recordatorio: El torneo comienza el {tournament.start_at.astimezone(pytz.timezone(player_timezone)).strftime('%d de %B')} a las {tournament.start_at.astimezone(pytz.timezone(player_timezone)).strftime('%H:%M')}. Te esperamos puntual."
                        )
                    except Exception as error:
                        logger.error(f'Error al enviar notificacion FCM de recordatorio de inicio del torneo de 2 horas antes" => {str(error)}')

                tournament.notification_1 = True
                tournament.save(update_fields=['notification_1'])
            
            ### Recordatorio de inicio 30 minutos antes
            diff_start = tournament.start_at - timedelta(minutes=30)
            if  diff_start < now and not tournament.notification_30 and int(player_in_tournament) == int(tournament.max_player):
                timezone_list = player_list.order_by("timezone").distinct("timezone").values_list("timezone", flat=True)
                for player_timezone in timezone_list:
                    players_id = player_list.filter(timezone=player_timezone).values_list("user__id", flat=True)
                    try:
                        safe_async_task(
                            async_send_fcm_message,
                            list(players_id),
                            "⏰ Recordatorio de inicio",
                            f"Recordatorio: El torneo comienza en 30 minutos, a las {tournament.start_at.astimezone(pytz.timezone(player_timezone)).strftime('%H:%M')}. ¡Prepárate para jugar!"
                        )
                    except Exception as error:
                        logger.error(f'Error al enviar notificacion FCM de recordatorio de inicio del torneo de 30 minutos antes" => {str(error)}')

                tournament.notification_30 = True
                tournament.save(update_fields=['notification_30'])
            
            ### Recordatorio de cierre de inscripciones 12 horas antes del cierre
            diff_deadline = tournament.deadline - timedelta(hours=12)
            if diff_deadline < now and not tournament.notification_12 and tournament.status == TournamentStatus.WAITING_PLAYERS[0]:
                timezone_list = player_list.order_by("timezone").distinct("timezone").values_list("timezone", flat=True)
                for player_timezone in timezone_list:
                    players_id = player_list.filter(timezone=player_timezone).values_list("user__id", flat=True)
                    try:
                        safe_async_task(
                            async_send_fcm_message,
                            list(players_id),
                            "⏰ Recordatorio de cierre de inscripciones",
                            f"Recordatorio: El registro del torneo cierra en 12 horas, el {tournament.deadline.astimezone(pytz.timezone(player_timezone)).strftime('%d de %B')} a las {tournament.deadline.astimezone(pytz.timezone(player_timezone)).strftime('%H:%M')}. ¡No te lo pierdas!"
                        )
                    except Exception as error:
                        logger.error(f'Error al enviar notificacion FCM de recordatorio de cierre de inscripciones del torneo de 12 horas antes" => {str(error)}')

                tournament.notification_12 = True
                tournament.save(update_fields=['notification_12'])

            ### Notificación a jugadores fuera del torneo para completar cupos
            if tournament.status == TournamentStatus.WAITING_PLAYERS[0] and player_in_tournament < tournament.max_player and  target_hour is not None and current_hour == target_hour and 0 <= current_minute < 10:
                free_places = tournament.max_player - player_in_tournament
                player_out_tournament = Player.objects.filter(send_game_notifications=True).annotate(
                                                                calculated_total_coins=(
                                                                    Coalesce(F('earned_coins'), Value(0)) + 
                                                                    Coalesce(F('recharged_coins'), Value(0))
                                                                ),
                                                                # Contamos en cuántos torneos ha participado
                                                                tournament_played= Count('player_list')
                                                            ).exclude(id__in=player_list.values_list('id', flat=True))
                
                if player_out_tournament.exists():
                    if free_places == 1:
                        players_to_notify_qs = player_out_tournament.filter(calculated_total_coins__gte=tournament.registration_fee).order_by("-tournament_played","-lastTimeInSystem")[:4]
                    else:
                        # Tomamos los más recientes y algunos aleatorios para completar
                        top_players_ids = list(player_out_tournament.filter(calculated_total_coins__gte=tournament.registration_fee).order_by("-tournament_played","-lastTimeInSystem")[:free_places].values_list('id', flat=True))
                        others_ids = list(player_out_tournament.exclude(id__in=top_players_ids).order_by("?")[:free_places].values_list('id', flat=True))
                        all_selected_ids = top_players_ids + others_ids
                        players_to_notify_qs = Player.objects.filter(id__in=all_selected_ids)
                    
                    timezone_list = players_to_notify_qs.order_by("timezone").distinct("timezone").values_list("timezone", flat=True)
                    for player_timezone in timezone_list:
                        target_players_ids = players_to_notify_qs.filter(timezone=player_timezone).values_list("user__id", flat=True)
                        if target_players_ids.exists():
                            fecha_cierre = tournament.deadline.astimezone(pytz.timezone(player_timezone)).strftime('%d-%m a las %H:%M')
                            
                            if free_places == 1:
                                titulo = "🚨 ¡ÚLTIMO CUPO disponible!"
                                cuerpo = f"Se está esperando por ti para empezar el Torneo. ¡Entra ya y compite por la victoria!"
                            elif free_places < 4:
                                titulo = "🏆 ¡Torneo de Dominó Casi lleno!"
                                cuerpo = f"¡Solo faltan {free_places} para empezar! Tienes saldo suficiente?. El registro cierra a las {fecha_cierre}."
                            else:
                                titulo = "🏆 ¡Torneo Abierto!"
                                cuerpo = f"Inscríbete ahora y asegura tu lugar. El registro cierra el {fecha_cierre}. ¡Usa tus monedas y gana!"

                            try:
                                safe_async_task(
                                    async_send_fcm_message,
                                    list(target_players_ids),
                                    titulo,
                                    cuerpo
                                )
                            except Exception as error:
                                logger.error(f'Error al enviar notificacion FCM de recordatorio de torneo abierto" => {str(error)}')