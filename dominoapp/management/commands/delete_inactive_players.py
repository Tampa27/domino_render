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
    help = "Delete players with an inactivity time greater than 30 days."

    def handle(self, *args, **options):
        expired_time = now() - timedelta(days= 30)
        
        players_models = Player.objects.filter(
            lastTimeInSystem__lt=expired_time,
            inactive_player = False
            ).only('email', 'inactive_player')

        for player in players_models[:100].iterator():
            if EmailConnector.email_inactive_players(player):
                player.inactive_player = True
                player.save(update_fields=['inactive_player'])

                DiscordConnector.send_event(
                    ApiConstants.AdminNotifyEvents.ADMIN_EVENT_EMAIL_DELETE_PLAYER.key,
                    params={
                        'email': player.email
                    }
                )
        
        expired_time = now() - timedelta(days= 37)
        players_models_delete = Player.objects.filter(
            lastTimeInSystem__lt=expired_time,
            inactive_player = True
            ).only('email', 'inactive_player', 'lastTimeInSystem')

        for player in players_models_delete.iterator():
            try:
                email_player = player.email
                player.delete()

                DiscordConnector.send_event(
                    "Eliminar Player Inactivo",
                    params={
                        'email': email_player
                    }
                )
            except Exception as error:
                logger.critical(f"El player {player.email} no se ha podido eliminar, ultima fecha en el sistema: {player.lastTimeInSystem.strftime('%d-%m-%Y, %H:%M:%S')}, causa del error: {str(error)}")


        return