import os
import pytz
from django.core.management.base import BaseCommand
from django.db.models import Q, F, Count, Value
from django.db.models.functions import Coalesce
from django.utils.timezone import timedelta
from django.utils import timezone
from dominoapp.models import Tournament, Player
from dominoapp.tasks import async_send_fcm_message, async_send_global_fcm_message
from dominoapp.utils.async_task_helper import enqueue_heavy_task
from dominoapp.utils.constants import TournamentStatus
import logging
logger = logging.getLogger("django")

DEFAULT_TZ = "America/Havana"

def _safe_timezone(tz_name):
    """Devuelve un tzinfo válido o el default si el nombre está corrupto."""
    if not tz_name or not isinstance(tz_name, str):
        return pytz.timezone(DEFAULT_TZ)
    try:
        return pytz.timezone(tz_name)
    except (pytz.UnknownTimeZoneError, AttributeError, ValueError):
        return pytz.timezone(DEFAULT_TZ)

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
            # Aislamos cada torneo: un torneo malo no debe tumbar el comando entero.
            try:
                self._process_tournament(
                    tournament=tournament,
                    now=now,
                    current_hour=current_hour,
                    current_minute=current_minute,
                    target_hour=target_hour,
                )
            except Exception as error:
                logger.exception(
                    "Error procesando el torneo %s en tournament_automatic => %s",
                    getattr(tournament, "id", "?"),
                    str(error),
                )
                continue


    def _process_tournament(self, tournament, now, current_hour, current_minute, target_hour):
        # Normalizamos fechas por si alguna quedó naive en BD.
        deadline = tournament.deadline
        start_at = tournament.start_at

        if deadline is None or start_at is None:
            logger.error(
                "Torneo %s sin deadline/start_at válidos, se omite.",
                tournament.id,
            )
            return

        # Guardas contra valores None en max/min player
        try:
            max_player = int(tournament.max_player)
            min_player = int(tournament.min_player)
        except (TypeError, ValueError):
            logger.error(
                "Torneo %s tiene max_player/min_player inválidos, se omite.",
                tournament.id,
            )
            return
        
        # analizar si el numero de player es par            
        player_list = tournament.player_list.all()
        player_in_tournament = player_list.count()
        # ------------------------------------------------------------------
        # 1) Correr el torneo 1 día por falta de jugadores
        # ------------------------------------------------------------------
        try:
            if (
                (deadline < now < start_at 
                 and player_in_tournament%2 != 0 
                 and int(player_in_tournament) < max_player) 
                or
                (deadline < now < start_at 
                 and int(player_in_tournament) < min_player)
            ):
                tournament.deadline += timedelta(days=1)
                tournament.start_at += timedelta(days=1)
                tournament.save(update_fields=['deadline', 'start_at'])

                deadline = tournament.deadline
                start_at = tournament.start_at

                timezone_list = player_list.order_by("timezone", "id").distinct("timezone").values_list("timezone", flat=True)
                for player_timezone in timezone_list:
                    tz = _safe_timezone(player_timezone)
                    
                    if player_timezone is None or player_timezone == "":
                        # NULL o "" -> jugadores sin zona definida
                        players_qs = player_list.filter(
                            Q(timezone__isnull=True) | Q(timezone="")
                        )
                    else:
                        players_qs = player_list.filter(timezone=player_timezone)
                    
                    players_id = list(players_qs.values_list("user__id", flat=True))
                    if not players_id:
                        continue
                    
                    enqueue_heavy_task(
                        async_send_fcm_message,
                        players_id, 
                        "⏰ Fechas del Torneo Corridas",
                        f"El torneo se pospuso para el {start_at.astimezone(tz).strftime('%d-%m-%Y, %H:%M')} debido a inscripciones incompletas. Las inscripciones siguen abiertas hasta el {deadline.astimezone(tz).strftime('%d-%m-%Y, %H:%M')}."
                    )
                
                try:
                    havana = pytz.timezone(DEFAULT_TZ)
                    enqueue_heavy_task(
                        async_send_global_fcm_message,
                        "⏰ Última oportunidad para inscribirte al torneo",
                        f"⏰ Se corrió el torneo. Ahora puedes unirte al torneo antes del {deadline.astimezone(havana).strftime('%d-%m a las %H:%M')}."
                    )
                except Exception as error:
                    logger.error(f'Error al enviar notificacion FCM global de cambio de fecha del torneo:=> {str(error)}')
        except Exception as error:
            logger.exception(
                "Error en bloque 'correr torneo' torneo=%s => %s",
                tournament.id, str(error)
            )

        # ------------------------------------------------------------------
        # 2) Recordatorio global de cierre de inscripciones (12h antes)
        # ------------------------------------------------------------------
        try:
            diff_deadline = tournament.deadline - timedelta(hours=12)
            if (
                diff_deadline < now 
                and not tournament.notification_deadline 
                and player_in_tournament < max_player
            ):
                try:
                    havana = pytz.timezone(DEFAULT_TZ)
                    enqueue_heavy_task(
                        async_send_global_fcm_message,
                        "⏰ Últimas horas para inscribirte al torneo",
                        f"⏰ Inscripciones a punto de cerrar. Únete al torneo antes del {deadline.astimezone(havana).strftime('%d-%m a las %H:%M')}."
                    )
                except Exception as error:
                        logger.error(f'Error al enviar notificacion FCM global de recordatorio de cierre de inscripciones:=> {str(error)}')
                
                tournament.notification_deadline = True
                tournament.save(update_fields=['notification_deadline'])
        except Exception as error:
            logger.exception(
                "Error en bloque 'recordatorio global cierre' torneo=%s => %s",
                tournament.id, str(error)
            )

        # ------------------------------------------------------------------
        # 3) Recordatorio de inicio 2 horas antes (solo si está lleno)
        # ------------------------------------------------------------------
        try:
            diff_start = tournament.start_at - timedelta(hours=2)
            if  (
                diff_start < now 
                and not tournament.notification_1 
                and int(player_in_tournament) == max_player
            ):
                timezone_list = player_list.order_by("timezone", "id").distinct("timezone").values_list("timezone", flat=True)
                for player_timezone in timezone_list:
                    tz = _safe_timezone(player_timezone)
                    
                    if player_timezone is None or player_timezone == "":
                        # NULL o "" -> jugadores sin zona definida
                        players_qs = player_list.filter(
                            Q(timezone__isnull=True) | Q(timezone="")
                        )
                    else:
                        players_qs = player_list.filter(timezone=player_timezone)
                    
                    players_id = list(players_qs.values_list("user__id", flat=True))
                    if not players_id:
                        continue
                    
                    try:
                        enqueue_heavy_task(
                            async_send_fcm_message,
                            players_id,
                            "⏰ Recordatorio de inicio",
                            f"Recordatorio: El torneo comienza el {start_at.astimezone(tz).strftime('%d de %B')} a las {start_at.astimezone(tz).strftime('%H:%M')}. Te esperamos puntual."
                        )
                    except Exception as error:
                        logger.error(f'Error al enviar notificacion FCM de recordatorio de inicio del torneo de 2 horas antes:=> {str(error)}')

                tournament.notification_1 = True
                tournament.save(update_fields=['notification_1'])
        except Exception as error:
            logger.exception(
                "Error en bloque 'recordatorio inicio 2h' torneo=%s => %s",
                tournament.id, str(error)
            )

        # ------------------------------------------------------------------
        # 4) Recordatorio de inicio 30 minutos antes (solo si está lleno)
        # ------------------------------------------------------------------
        try:
            diff_start = tournament.start_at - timedelta(minutes=30)
            if  (
                diff_start < now 
                and not tournament.notification_30 
                and int(player_in_tournament) == max_player
            ):
                timezone_list = player_list.order_by("timezone", "id").distinct("timezone").values_list("timezone", flat=True)
                for player_timezone in timezone_list:
                    tz = _safe_timezone(player_timezone)
                    
                    if player_timezone is None or player_timezone == "":
                        # NULL o "" -> jugadores sin zona definida
                        players_qs = player_list.filter(
                            Q(timezone__isnull=True) | Q(timezone="")
                        )
                    else:
                        players_qs = player_list.filter(timezone=player_timezone)
                    
                    players_id = list(players_qs.values_list("user__id", flat=True))
                    if not players_id:
                        continue

                    try:
                        enqueue_heavy_task(
                            async_send_fcm_message,
                            players_id,
                            "⏰ Recordatorio de inicio",
                            f"Recordatorio: El torneo comienza en 30 minutos, a las {start_at.astimezone(tz).strftime('%H:%M')}. ¡Prepárate para jugar!"
                        )
                    except Exception as error:
                        logger.error(f'Error al enviar notificacion FCM de recordatorio de inicio del torneo de 30 minutos antes:=> {str(error)}')

                tournament.notification_30 = True
                tournament.save(update_fields=['notification_30'])
        except Exception as error:
            logger.exception(
                "Error en bloque 'recordatorio inicio 30m' torneo=%s => %s",
                tournament.id, str(error)
            )


        # ------------------------------------------------------------------
        # 5) Notificación a jugadores fuera del torneo para completar cupos
        # ------------------------------------------------------------------
        try:
            if (
                tournament.status == TournamentStatus.WAITING_PLAYERS[0] 
                and player_in_tournament < max_player 
                and  target_hour is not None 
                and current_hour == target_hour 
                and 0 <= current_minute < 10
            ):
                free_places = max_player - player_in_tournament
                player_out_tournament = Player.objects.filter(
                    send_game_notifications=True
                ).annotate(
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
                    
                    timezone_list = players_to_notify_qs.order_by("timezone", "id").distinct("timezone").values_list("timezone", flat=True)
                    for player_timezone in timezone_list:
                        tz = _safe_timezone(player_timezone)

                        if player_timezone is None or player_timezone == "":
                            # NULL o "" -> jugadores sin zona definida
                            players_qs = players_to_notify_qs.filter(
                                Q(timezone__isnull=True) | Q(timezone="")
                            )
                        else:
                            players_qs = players_to_notify_qs.filter(timezone=player_timezone)
                        
                        target_players_ids = list(players_qs.values_list("user__id", flat=True))
                        if not target_players_ids:
                            continue
                        
                        fecha_cierre = deadline.astimezone(tz).strftime('%d-%m a las %H:%M')
                        
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
                            enqueue_heavy_task(
                                async_send_fcm_message,
                                target_players_ids,
                                titulo,
                                cuerpo
                            )
                        except Exception as error:
                            logger.error(f'Error al enviar notificacion FCM de recordatorio de torneo abierto" => {str(error)}')
        except Exception as error:
            logger.exception(
                "Error en bloque 'notificacion cupos libres' torneo=%s => %s",
                tournament.id, str(error)
            )