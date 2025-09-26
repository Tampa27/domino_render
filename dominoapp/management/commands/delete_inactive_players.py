import os
import django
from dominoapp.connectors.discord_connector import DiscordConnector
from dominoapp.utils.constants import ApiConstants

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from dominoapp.models import Player
from dominoapp.connectors.email_connector import EmailConnector
import logging
logger = logging.getLogger('django')


class Command(BaseCommand):
    help = "Delete players with an inactivity time greater than 60 days."

    def handle(self, *args, **options):
        expired_time = now() - timedelta(days= 60)
        
        players_models = Player.objects.filter(
            lastTimeInSystem__lt=expired_time,
            send_delete_email = False
            ).only('email', 'send_delete_email')

        for player in players_models[:100].iterator():
            expiration_time = now() + timedelta(days=30)
            if EmailConnector.email_inactive_players(player, expiration_time):
                player.send_delete_email = True
                player.save(update_fields=['send_delete_email'])

                DiscordConnector.send_event(
                    ApiConstants.AdminNotifyEvents.ADMIN_EVENT_EMAIL_DELETE_PLAYER.key,
                    params={
                        'email': player.email,
                        'days': 30
                    }
                )
        
        expired_time = now() - timedelta(days= 83)        
        players_models = Player.objects.filter(
            lastTimeInSystem__lt=expired_time,
            send_delete_email = True
            ).only('email', 'inactive_player')

        for player in players_models[:100].iterator():
            expiration_time = now() + timedelta(days=7)
            if EmailConnector.email_inactive_players(player, expiration_time):
                player.inactive_player = True
                player.save(update_fields=['inactive_player'])

                DiscordConnector.send_event(
                    ApiConstants.AdminNotifyEvents.ADMIN_EVENT_EMAIL_DELETE_PLAYER.key,
                    params={
                        'email': player.email,
                        'days': 7
                    }
                )

        expired_time = now() - timedelta(days= 90)
        players_models_delete = Player.objects.filter(
            lastTimeInSystem__lt=expired_time,
            inactive_player = True
            ).only('email')

        for player in players_models_delete.iterator():
            try:
                email_player = player.email
                player.user.delete()

                DiscordConnector.send_event(
                    "Eliminar Player Inactivo",
                    params={
                        'email': email_player
                    }
                )
            except Exception as error:
                logger.critical(f"El player {player.email} no se ha podido eliminar, ultima fecha en el sistema: {player.lastTimeInSystem.strftime('%d-%m-%Y, %H:%M:%S')}, causa del error: {str(error)}")


        return