import time
import sys
import os
from dominoapp import views
from dominoapp.models import Player
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        
        player = Player.objects.get(alias="mariocondepr")
        player.coins-=1
        player.save()
        time.sleep(10)
        return super().handle(*args, **options)
      
