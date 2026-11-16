import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from django.db import transaction as db_transaction
from dominoapp.models import MoveRegister


BATCH = 500


class Command(BaseCommand):
    help = "Delete MoveRegister records with time created greater than 2 days."

    def handle(self, *args, **options):
        expired_time = now() - timedelta(days=2)

        qs = MoveRegister.objects.filter(time__lt=expired_time)

        total_deleted = 0
        while True:
            ids = list(qs.values_list('id', flat=True)[:BATCH])
            if not ids:
                break
            with db_transaction.atomic():
                deleted, _ = MoveRegister.objects.filter(id__in=ids).delete()
            total_deleted += deleted
            self.stdout.write(f"Lote eliminado: {deleted} (total: {total_deleted})")

        self.stdout.write(f"MoveRegister eliminados: {total_deleted}")