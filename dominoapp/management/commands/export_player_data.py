import os
import base64
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from django.core.management.base import BaseCommand, CommandError
from django.db.models import F

from dominoapp.models import Player
from dominoapp.utils.template_player_export import create_xlsx_file
from dominoapp.utils.async_task_helper import enqueue_heavy_task
from dominoapp.tasks import async_email_players_backup


class Command(BaseCommand):
    help = "Export the players data as XLSX and email it as an attachment."

    def handle(self, *args, **options):
        qs = (
            Player.objects
            .annotate(total_coins_filter=F('earned_coins') + F('recharged_coins'))
            .filter(total_coins_filter__gte=50)
            .only('id', 'alias', 'earned_coins', 'recharged_coins',
                  'email', 'name', 'lastTimeInSystem')
        )

        if not qs.exists():
            raise CommandError('There are no players to export.')

        # 1. Contar jugadores (una sola consulta COUNT)
        total_players = qs.count()
        self.stdout.write(f"Jugadores a exportar: {total_players}")

        # 2. Generar el XLSX en streaming (sin cargar todo en memoria)
        self.stdout.write("Generando XLSX...")
        xlsx_bytes = create_xlsx_file(
            'Players_Backup',
            qs.iterator(chunk_size=1000),
        )
        self.stdout.write(f"XLSX generado: {len(xlsx_bytes)} bytes")

        # 3. Codificar en base64 para que Celery/JSON lo pueda transportar
        xlsx_b64 = base64.b64encode(xlsx_bytes).decode('ascii')

        # 4. Encolar el email (no bloquea el comando)
        enqueue_heavy_task(async_email_players_backup, xlsx_b64, total_players)
        self.stdout.write("Email de backup encolado.")

        return