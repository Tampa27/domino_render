import sys
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from django.db.models import Q, Count
from dominoapp.models import DominoGame, MatchGame, DataGame
from dominoapp.utils.game_tools import playersCount

class Command(BaseCommand):
    help = "Delete games with an inactivity time greater than 10 hours."

    def handle(self, *args, **options):
        expired_time = now() - timedelta(hours = 10)
              
        datas_game = DataGame.objects.filter(
            active= True,
            start_time__lt=expired_time
        ).exclude(match__domino_game__id__in=[2,3,4,5,18,21,497,475,639,652])

        for data in datas_game:
            if len(playersCount(data)) == 0:
                if data.match.domino_game:
                    data.match.domino_game.delete()
                if data.match:
                    data.match.delete()
                data.delete()
        return