import sys
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from dominoapp.models import DominoGame
from dominoapp.views import playersCount

class Command(BaseCommand):
    help = "Delete games with an inactivity time greater than 10 hours."

    def handle(self, *args, **options):
        expired_time = now() - timedelta(hours = 10)
        
        games_models = DominoGame.objects.filter(
            start_time__lt=expired_time
            ).exclude(id__in=[2,3,4,5,18,21,497,475,639,652])

        for game in games_models:
            if len(playersCount(game)) == 0:
                game.delete()
        return