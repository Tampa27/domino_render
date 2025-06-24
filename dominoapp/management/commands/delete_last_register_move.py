from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from dominoapp.models import MoveRegister

class Command(BaseCommand):
    help = "Delete transactions with time created greater than 1 week."

    def handle(self, *args, **options):
        expired_time = now() - timedelta(days= 2)
        
        register_models = MoveRegister.objects.filter(
            time__lt=expired_time
            )

        for register_move in register_models.iterator():
            register_move.delete()
        return