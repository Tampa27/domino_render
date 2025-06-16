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


class Command(BaseCommand):
    help = "Delete players with an inactivity time greater than 30 days."

    def handle(self, *args, **options):
        expired_time = now() - timedelta(days= 30)
        
        players_models = Player.objects.filter(
            lastTimeInSystem__lt=expired_time,
            inactive_player = False
            )

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

        return