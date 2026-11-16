import sys
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from dominoapp.models import DominoGame
from dominoapp.utils.game_tools import playersCount

class Command(BaseCommand):
    help = "Delete games with an inactivity time greater than 10 hours."

    def handle(self, *args, **options):
        expired_time = now() - timedelta(hours = 10)
        
        fix_game_ids = os.environ.get('FIX_GAME_IDS', '2,3,4,5,18,21,497,475')
        game_ids = [int(x) for x in fix_game_ids.split(',') if x.strip().isdigit()]
        
        qs = DominoGame.objects.filter(
                start_time__lt=expired_time
            ).exclude(id__in=game_ids).filter(
                player1__isnull=True,
                player2__isnull=True,
                player3__isnull=True,
                player4__isnull=True
            )

        BATCH = 500
        total_deleted = 0
        while True:
            ids = list(qs.values_list('id', flat=True)[:BATCH])
            if not ids:
                break
            deleted, _ = DominoGame.objects.filter(id__in=ids).delete()
            total_deleted += deleted
            self.stdout.write(f"Lote eliminado: {deleted} objetos (total: {total_deleted})")

        self.stdout.write(f"Juegos eliminados: {total_deleted}")

        return