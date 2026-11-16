import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from django.db import transaction as db_transaction
from django.db.models import OuterRef, Exists
from django.db.models.deletion import ProtectedError

from dominoapp.models import Player, BlockPlayer
from dominoapp.connectors.discord_connector import DiscordConnector
from dominoapp.utils.async_task_helper import enqueue_heavy_task
from dominoapp.tasks import async_send_inactive_player_email

import logging
logger = logging.getLogger('django')


BATCH = 100


def _base_qs(expired_time, extra_filters):
    return (
        Player.objects
        .annotate(
            is_blocked=Exists(
                BlockPlayer.objects.filter(player_blocked=OuterRef('pk'))
            )
        )
        .filter(
            lastTimeInSystem__lt=expired_time,
            is_blocked=False,
            **extra_filters,
        )
    )


class Command(BaseCommand):
    help = "Delete players with an inactivity time greater than 60 days."

    def handle(self, *args, **options):
        # ------------------------------------------------------------------
        # Fase 1: aviso 30 días → encolar email + Discord
        # ------------------------------------------------------------------
        expired_time = now() - timedelta(days=60)
        qs1 = _base_qs(expired_time, {
            'send_delete_email': False,
            'inactive_player': False,
        }).only('id', 'email', 'send_delete_email')

        queued = 0
        for player in qs1[:100].iterator(chunk_size=100):
            enqueue_heavy_task(
                async_send_inactive_player_email,
                player.id,
                player.email,
                30,
                "warning_30",
            )
            queued += 1
        self.stdout.write(f"[Fase 1] emails encolados: {queued}")

        # ------------------------------------------------------------------
        # Fase 2: aviso 7 días → encolar email + Discord
        # ------------------------------------------------------------------
        expired_time = now() - timedelta(days=83)
        qs2 = _base_qs(expired_time, {
            'send_delete_email': True,
            'inactive_player': False,
        }).only('id', 'email', 'inactive_player')

        queued = 0
        for player in qs2[:100].iterator(chunk_size=100):
            enqueue_heavy_task(
                async_send_inactive_player_email,
                player.id,
                player.email,
                7,
                "warning_7",
            )
            queued += 1
        self.stdout.write(f"[Fase 2] emails encolados: {queued}")

        # ------------------------------------------------------------------
        # Fase 3: borrado real (>90 días, send_delete_email=True, inactive=True)
        # ------------------------------------------------------------------
        expired_time = now() - timedelta(days=90)
        qs3 = _base_qs(expired_time, {
            'send_delete_email': True,
            'inactive_player': True,
        }).only('id', 'email', 'user_id')

        total_deleted = 0
        total_protected = 0
        total_errors = 0

        from django.contrib.auth.models import User

        while True:
            ids = list(qs3.values_list('id', flat=True)[:BATCH])
            if not ids:
                break

            rows = list(
                Player.objects.filter(id__in=ids)
                .values_list('id', 'user_id', 'email')
            )

            for player_id, user_id, email in rows:
                try:
                    with db_transaction.atomic():
                        User.objects.filter(id=user_id).delete()
                    total_deleted += 1
                    # Discord en background (no bloquea el borrado)
                    enqueue_heavy_task(
                        DiscordConnector.send_event,
                        "Eliminar Player Inactivo",
                        params={'email': email},
                    )
                except ProtectedError as e:
                    total_protected += 1
                    logger.warning(
                        f"Fase 3: player {email} (id={player_id}) no se puede borrar "
                        f"por ProtectedError: {e}"
                    )
                except Exception as e:
                    total_errors += 1
                    logger.critical(
                        f"Fase 3: error borrando player {email} (id={player_id}): {e}"
                    )

            self.stdout.write(
                f"[Fase 3] borrados={total_deleted}, "
                f"protegidos={total_protected}, errores={total_errors}"
            )

        self.stdout.write(
            f"[Fase 3] TOTAL: borrados={total_deleted}, "
            f"protegidos={total_protected}, errores={total_errors}"
        )