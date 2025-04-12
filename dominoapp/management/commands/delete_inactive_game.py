from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from django.db.models import Q
from dominoapp.models import DominoGame

class Command(BaseCommand):
    help = "Delete games with an inactivity time greater than 24 hours."

    def handle(self, *args, **options):
        expired_time = now() - timedelta(hours = 24)
        
        games_models = DominoGame.objects.filter(
            lastTime1__lt=expired_time,
            lastTime2__lt=expired_time,
            lastTime3__lt=expired_time,
            lastTime4__lt=expired_time
            ).exclude(id__in=[33,36,55])

        for game in games_models:
            game.delete()

        return