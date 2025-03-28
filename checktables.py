import time
import sys
import os
import django

# Configurar entorno Django
PROJECT_ROOT = '/home/ahmedlp9/domino_render'
sys.path.append(PROJECT_ROOT)  # Ruta absoluta a tu proyecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from dominoapp import views
from dominoapp.models import Player
from dominoapp.models import DominoGame
from django.utils import timezone
# Importar tus módulos después de configurar Django
#from tu_app import tasks  # Ejemplo de importación

moveWait = 2
waitPatner = 7
waitWinner = 7
passWait = 2
def main():
    while True:
        games = DominoGame.objects.all()
        for game in games:
            players = views.playersCount(players)
            players_running = list(filter(lambda p: p.isPlaying, players))
            if game.status == 'ru':
                possibleStarter = (game.inPairs and game.startWinner and game.winner >= 4)
                if possibleStarter:
                    automaticCoupleStarter(game,players)
                else:
                    automaticMove(game,players_running)    


        time.sleep(5)
        
def automaticCoupleStarter(game,players):
    next = game.next_player
    patner = (next+2)%4
    player_w = players[next]
    player_p = players[patner]
    starter = game.starter
    time_diff1 = timezone.now() - player_p.lastTimeInSystem
    time_diff2 = timezone.now() - player_w.lastTimeInSystem
    if time_diff1.seconds > waitPatner and starter == next:
        views.setWinner1(game.id,next)
    elif time_diff2.seconds > waitWinner and starter != next:
        views.setWinnerStarterNext1(game.id,patner,patner,patner)     

def automaticMove(game,players):
    next = game.next_player
    player_w = players[next]
    moveTime = game.moveTime
    time_diff = timezone.now() - player_w.lastTimeInSystem
    if len(game.board) == 0:
        tile = views.takeRandomTile(player_w.tiles)
        if time_diff.seconds > (moveTime+moveWait): 
            views.movement(game,player_w,players,tile)
            views.updateLastPlayerTime(game,player_w.alias)
    else:
        tile = views.takeRandomCorrectTile(player_w.tiles,game.leftValue,game.rightValue)
        if views.isPass(tile):
            if time_diff.seconds > passWait:
                views.movement(game,player_w,players,tile)
                views.updateLastPlayerTime(game,player_w.alias) 
        elif time_diff.seconds > (moveTime+moveWait):                     
            views.movement(game,player_w,players,tile)
            views.updateLastPlayerTime(game,player_w.alias)        


if __name__ == "__main__":
    main()      
