from django.core.management.base import BaseCommand
from dominoapp.models import Bank
from datetime import datetime


class Command(BaseCommand):
    help = "Create every 1st month day a new Bank to resume stadistic."

    def handle(self, *args, **options):
        day = datetime.now().day
        if day == 1:
            Bank.objects.create()

        return