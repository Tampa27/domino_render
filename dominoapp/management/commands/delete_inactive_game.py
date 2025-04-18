from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from django.db.models import Q
from dominoapp.models import DominoGame
from dominoapp.views import playersCount

class Command(BaseCommand):
    help = "Delete games with an inactivity time greater than 24 hours."

    def handle(self, *args, **options):
        expired_time = now() - timedelta(hours = 15)
        
        games_models = DominoGame.objects.filter(
            start_time__lt=expired_time
            ).exclude(id__in=[33,36,55])

        for game in games_models:
            if playersCount(game) == 0:
                game.delete()
        return