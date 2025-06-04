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
from django.db import transaction
# Importar tus módulos después de configurar Django
#from tu_app import tasks  # Ejemplo de importación

moveWait = 3
waitPatner = 7
waitWinner = 7
passWait = 2
startWait = 10
exitgame = 300

import logging

def main():
    while True:
        time_sleep = 6
        games = DominoGame.objects.all()
        all_game = games.count()
        
        wt_game = games.filter(status = "wt").count()
        if wt_game == all_game:
            time_sleep = 15

        logging.info(f"time_sleep = {time_sleep}")
        
        for game in games:
            players = views.playersCount(game)
            players_running = list(filter(lambda p: p.isPlaying, players))
            if game.status == 'ru':
                possibleStarter = (game.inPairs and game.startWinner and game.winner >= 4)
                if possibleStarter:
                    logging.info('Esperando al salidor')
                    try:
                        automaticCoupleStarter(game)
                    except Exception:
                        logging.error('Ocurrio una excepcion escogiendo el salidor en el juego '+str(game.id))        
                else:
                    try:
                        automaticMove(game,players_running)
                    except Exception:
                        logging.error('Ocurrio una excepcion moviendo una ficha en el juego '+str(game.id))    
            elif (game.status == 'fg' and game.perPoints == False) or game.status == 'fi':
                try:
                    restargame = True
                    if game.status == 'fg':
                        for player in players_running:
                            diff_time = timezone.now() - player.lastTimeInSystem
                            if (diff_time.seconds >= views.exitTime) and player.isPlaying:
                                views.exitPlayer(game,player,players,len(players))
                        players = views.playersCount(game)
                        if len(players)<1:
                            restargame = False
                    if restargame:
                        automaticStart(game,players)
                except Exception:
                    logging.error('Ocurrio una excepcion comenzando la mesa '+str(game.id))    
            elif game.status == 'fg' or game.status == 'wt' or game.status == 'ready':
                for player in players:
                    diff_time = timezone.now() - player.lastTimeInSystem
                    if (diff_time.seconds >= views.exitTime) and player.isPlaying:
                        views.exitPlayer(game,player,players,len(players))
                    elif (diff_time.seconds >= exitgame):
                        views.exitPlayer(game,player,players,len(players))
                
                game.refresh_from_db()
                if game.status == 'wt' and len(players)<2:
                    game.starter=-1
                    game.board = ""
                    game.save()

        time.sleep(time_sleep)
        
def automaticCoupleStarter(game):
    next = game.next_player
    patner = (next+2)%4
    starter = game.starter
    lastMoveTime = lastMove(game)
    time_diff1 = timezone.now() - lastMoveTime
    logging.error("Entro a automaticCouple")
    logging.error("La diferencia de tiempo es "+ str(time_diff1.seconds))
    if time_diff1.seconds > waitPatner and starter == next:
        views.setWinner1(game,next)
    elif time_diff1.seconds > waitWinner and starter != next:
        views.setWinnerStarterNext1(game,patner,patner,patner)
    game.save()         

def automaticMove(game,players):
    next = game.next_player
    player_w = players[next]
    moveTime = game.moveTime
    time_diff = timezone.now() - lastMove(game)
    if len(game.board) == 0:
        tile = views.takeRandomTile(player_w.tiles)
        if time_diff.seconds > (moveTime+moveWait):
            try:
                # with transaction.atomic():
                error = views.movement(game.id,player_w.id,players,tile)
                if error is not None:
                    logging.error(f"Error en el movimiento automatico, message: {error})")
                views.updateLastPlayerTime(game,player_w.alias)  
                #views.move1(game.id,player_w.alias,tile)
            except Exception as e:
                logging.error("Error en el movimiento automatico "+str(e))            
            #views.updateLastPlayerTime(game,player_w.alias)
    else:
        tile = views.takeRandomCorrectTile(player_w.tiles,game.leftValue,game.rightValue)
        if views.isPass(tile):
            if time_diff.seconds > passWait:
                try:
                    # with transaction.atomic():
                    error = views.movement(game.id,player_w.id,players,tile)
                    if error is not None:
                        logging.error(f"Error en el movimiento automatico, message: {error})")
                    views.updateLastPlayerTime(game,player_w.alias)  
                    #views.move1(game.id,player_w.alias,tile)
                except Exception as e:
                    logging.error("Error en el movimiento automatico "+str(e))
                #views.movement(game,player_w,players,tile)
                #views.updateLastPlayerTime(game,player_w.alias) 
        elif time_diff.seconds > (moveTime+moveWait):
            try:
                # with transaction.atomic():
                error = views.movement(game.id,player_w.id,players,tile)
                if error is not None:
                    logging.error(f"Error en el movimiento automatico, message: {error})")
                views.updateLastPlayerTime(game,player_w.alias)  
                #views.move1(game.id,player_w.alias,tile)
            except Exception as e:
                logging.error("Error en el movimiento automatico "+str(e))                     
            #views.movement(game,player_w,players,tile)
            #views.updateLastPlayerTime(game,player_w.alias)        
    # game.save()

def lastMove(game):
    res = game.start_time
    if game.lastTime1 is not None and game.lastTime1 > res:
        res = game.lastTime1
    if game.lastTime2 is not None and game.lastTime2 > res:
        res = game.lastTime2
    if game.lastTime3 is not None and game.lastTime3 > res:
        res = game.lastTime3
    if game.lastTime4 is not None and game.lastTime4 > res:
        res = game.lastTime4
    return res                

def automaticStart(game,players):
    lastMoveTime = lastMove(game)
    time_diff = timezone.now() - lastMoveTime
    if time_diff.seconds > startWait:
        views.startGame1(game,players)

if __name__ == "__main__":
    main()      
