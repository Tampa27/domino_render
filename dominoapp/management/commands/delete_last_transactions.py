import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from django.db import transaction as db_transaction
from django.db.models import OuterRef, Subquery
from dominoapp.models import Transaction, Status_Transaction


BATCH = 500


def _delete_transactions_in_batches(qs, batch=BATCH):
    """Borra transacciones en lotes, primero los status asociados, luego las transacciones."""
    total_tx = 0
    total_status = 0
    while True:
        ids = list(qs.values_list('id', flat=True)[:batch])
        if not ids:
            break
        with db_transaction.atomic():
            # 1. Borrar los status asociados a estas transacciones (M2M)
            status_ids = list(
                Status_Transaction.objects
                .filter(status_transaction__id__in=ids)
                .values_list('id', flat=True)
                .distinct()
            )
            if status_ids:
                deleted_status, _ = Status_Transaction.objects.filter(id__in=status_ids).delete()
                total_status += deleted_status
            # 2. Borrar las transacciones en bloque
            deleted_tx, _ = Transaction.objects.filter(id__in=ids).delete()
            total_tx += deleted_tx
    return total_tx, total_status


class Command(BaseCommand):
    help = """
        Delete game transactions with time created greater than 1 week.
        Delete transactions with time created greater than 3 month.
        """

    def handle(self, *args, **options):
        # ------------------------------------------------------------------
        # 1) Borrar transacciones de juego ('gm') con más de 1 semana
        # ------------------------------------------------------------------
        expired_time = now() - timedelta(weeks=1)
        qs_gm = Transaction.objects.filter(type='gm', time__lt=expired_time)
        tx, st = _delete_transactions_in_batches(qs_gm)
        self.stdout.write(f"[gm] Transacciones borradas: {tx}, status borrados: {st}")

        # ------------------------------------------------------------------
        # 2) Marcar como canceladas ('cc') las transacciones 'rl' y 'ex'
        #    con más de 24h y último status 'p'
        # ------------------------------------------------------------------
        expired_time = now() - timedelta(hours=24)
        qs_pending = (
            Transaction.objects
            .filter(type__in=['rl', 'ex'], time__lt=expired_time)
            .annotate(latest_status_name=Subquery(
                Status_Transaction.objects
                .filter(status_transaction=OuterRef('pk'))
                .order_by('-created_at')
                .values('status')[:1]
            ))
            .filter(latest_status_name='p')
        )

        # Creamos un único Status_Transaction 'cc' y lo asociamos en bloque
        # a todas las transacciones pendientes. OJO: Status_Transaction es un
        # modelo sin relación inversa directa; para asociarlo en bloque hay que
        # insertar en la tabla M2M. La forma más limpia es crear un status por
        # transacción, pero eso son N INSERTs. Alternativa: crear un solo
        # status y usar bulk_create en la tabla intermedia.
        pending_ids = list(qs_pending.values_list('id', flat=True))
        if pending_ids:
            cc_status = Status_Transaction.objects.create(status='cc')
            # Tabla M2M intermedia entre Transaction y Status_Transaction
            ThroughModel = Transaction.status_list.through
            through_rows = [
                ThroughModel(transaction_id=tx_id, status_transaction_id=cc_status.id)
                for tx_id in pending_ids
            ]
            ThroughModel.objects.bulk_create(through_rows, batch_size=BATCH, ignore_conflicts=True)
            self.stdout.write(f"[rl/ex] Transacciones marcadas como 'cc': {len(pending_ids)}")

        # ------------------------------------------------------------------
        # 3) Borrar transacciones con más de 12 semanas
        # ------------------------------------------------------------------
        expired_time = now() - timedelta(weeks=12)
        qs_old = Transaction.objects.filter(time__lt=expired_time)
        tx, st = _delete_transactions_in_batches(qs_old)
        self.stdout.write(f"[old] Transacciones borradas: {tx}, status borrados: {st}")

        return