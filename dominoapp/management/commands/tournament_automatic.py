import pytz
from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta
from django.utils import timezone
from dominoapp.models import Tournament
from dominoapp.utils.fcm_message import FCMNOTIFICATION
import logging
logger = logging.getLogger("django")


class Command(BaseCommand):
    help = "Check the tournaments that are active and check the number of players and send some notifications to the players."

    def handle(self, *args, **options):
        tournaments = Tournament.objects.filter(active=True).prefetch_related(
            'player_list__user'           # Para notificaciones a todos los inscritos
        )
        for tournament in tournaments:
            # analizar si el numero de player es par
            now = timezone.now()
            player_list = tournament.player_list.all()
            player_in_tournament = player_list.count()
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
                for player in player_list:
                    FCMNOTIFICATION.send_fcm_message(
                        user= player.user,
                        title= "⏰ Fechas del Torneo Corridas",
                        body=f"El torneo se pospuso para el {tournament.start_at.astimezone(pytz.timezone(player.timezone)).strftime('%d-%m-%Y, %H:%M')} debido a inscripciones incompletas. Las inscripciones siguen abiertas hasta el {tournament.deadline.astimezone(pytz.timezone(player.timezone)).strftime('%d-%m-%Y, %H:%M')}."
                    )
                
                FCMNOTIFICATION.send_fcm_global_message(
                    title="⏰ Última oportunidad para inscribirte al torneo",
                    body= f"⏰ Se corrió el torneo. Ahora puedes unirte al torneo antes del {tournament.deadline.astimezone(pytz.timezone('America/Havana')).strftime('%d-%m a las %H:%M')}."
                )
            
            diff_deadline = tournament.deadline - timedelta(hours=12)
            if (
                diff_deadline < now and not tournament.notification_deadline and
                player_in_tournament < int(tournament.max_player)
                ):
                FCMNOTIFICATION.send_fcm_global_message(
                    title="⏰ Últimas horas para inscribirte al torneo",
                    body= f"⏰ Inscripciones a punto de cerrar. Únete al torneo antes del {tournament.deadline.astimezone(pytz.timezone('America/Havana')).strftime('%d-%m a las %H:%M')}."
                )
                tournament.notification_deadline = True
                tournament.save(update_fields=['notification_deadline'])

            diff_start = tournament.start_at - timedelta(hours=2)
            if  diff_start < now and not tournament.notification_1:
                for player in player_list:
                    FCMNOTIFICATION.send_fcm_message(
                        user= player.user,
                        title= "⏰ Recordatorio de inicio",
                        body=f"Recordatorio: El torneo comienza el {tournament.start_at.astimezone(pytz.timezone(player.timezone)).strftime('%d de %B')} a las {tournament.start_at.astimezone(pytz.timezone(player.timezone)).strftime('%H:%M')}. Te esperamos puntual."
                    )
                tournament.notification_1 = True
                tournament.save(update_fields=['notification_1'])
            
            diff_start = tournament.start_at - timedelta(minutes=30)
            if  diff_start < now and not tournament.notification_30:
                for player in player_list:
                    FCMNOTIFICATION.send_fcm_message(
                        user= player.user,
                        title= "⏰ Recordatorio de inicio",
                        body=f"Recordatorio: El torneo comienza en 30 minutos, a las {tournament.start_at.astimezone(pytz.timezone(player.timezone)).strftime('%H:%M')}. ¡Prepárate para jugar!"
                    )
                tournament.notification_30 = True
                tournament.save(update_fields=['notification_30'])
            