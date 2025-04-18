from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from dominoapp.models import Transaction

class Command(BaseCommand):
    help = "Delete transactions with time created greater than 1 week."

    def handle(self, *args, **options):
        expired_time = now() - timedelta(weeks= 1)
        
        transaction_models = Transaction.objects.filter(
            type = 'gm',
            time__lt=expired_time
            )

        for transaction in transaction_models:
            transaction.delete()
        return