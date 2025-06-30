from django.core.management.base import BaseCommand
from django.db.models import F
from django.http import HttpResponse
from dominoapp.models import Player
from dominoapp.utils.template_player_export import create_xlsx_file

class Command(BaseCommand):
    help = "Export the players data."

    def handle(self, *args, **options):
                
        players_model = Player.objects.annotate(total_coins_filter=(F('earned_coins') + F('recharged_coins'))).filter(total_coins_filter__gte = 50).only(
            'alias',
            'earned_coins',
            'recharged_coins',
            'email',
            'name',
            'lastTimeInSystem'
            )

        if players_model.count() == 0:
            raise('There are no players to export.')
        
        return create_xlsx_file('Players_Backup', players_model.iterator())
        