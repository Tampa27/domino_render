import time
import sys
import os
from dominoapp import views
from dominoapp.models import Player

def main():
    while True:
        player = Player.objects.get(alias="mariocondepr")
        player.coins-=1
        player.save()
        time.sleep(10)
if __name__ == "__main__":
    main()        
