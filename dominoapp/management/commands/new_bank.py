from django.core.management.base import BaseCommand
from dominoapp.models import Bank


class Command(BaseCommand):
    help = "Create a new Bank to resume stadistic."

    def handle(self, *args, **options):

        Bank.objects.create()

        return