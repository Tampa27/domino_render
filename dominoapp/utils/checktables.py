import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from dominoapp.utils import game_tools
from dominoapp.models import DominoGame
from django.utils import timezone
from django.db import connection
from dominoapp.utils.constants import ApiConstants
import logging
logger = logging.getLogger('django')
logger_api = logging.getLogger(__name__)

def automatic_move_in_game():
    try:
        logger_api.info(f"Automatic Move Tile")
        
        games = DominoGame.objects.filter(player1__isnull=False).select_related(
            'player1',  # Precarga player1
            'player2',  # Precarga player2
            'player3',  # Precarga player3
            'player4'   # Precarga player4
        ).iterator()
        
        for game in games:
            players = game_tools.playersCount(game)
            players_running = list(filter(lambda p: p.isPlaying, players))
            if game.status == 'ru':
                possibleStarter = (game.inPairs and game.startWinner and game.winner >= 4)
                if possibleStarter:
                    logger_api.info('Esperando al salidor')
                    try:
                        automaticCoupleStarter(game)
                    except Exception as e:
                        logger.critical(f'Ocurrio una excepcion escogiendo el salidor en el juego {str(game.id)}, error: {str(e)}')        
                else:
                    try:
                        automaticMove(game,players_running)
                    except Exception as e:
                        logger.critical(f'Ocurrio una excepcion moviendo una ficha en el juego {str(game.id)},\n Data:(player_index: {game.next_player}, playes_in: {len(players_running)} ),\n error: {str(e)}')    
            elif (game.status == 'fg' and game.perPoints == False) or game.status == 'fi':
                try:
                    restargame = True
                    if game.status == 'fg':
                        for player in players_running:
                            diff_time = timezone.now() - player.lastTimeInSystem
                            if (diff_time.seconds >= ApiConstants.EXIT_GAME_TIME or not game_tools.ready_to_play(game,player)) and player.isPlaying:
                                game_tools.exitPlayer(game,player,players,len(players))
                        players = game_tools.playersCount(game)
                        if len(players)<2:
                            restargame = False
                    if restargame:
                        automaticStart(game,players)
                except Exception as e:
                    logger.critical(f'Ocurrio una excepcion comenzando el juego en la mesa {str(game.id)}, error: {str(e)}')    
            elif game.status == 'fg' or game.status == 'wt' or game.status == 'ready':
                for player in players:
                    diff_time = timezone.now() - player.lastTimeInSystem
                    if (diff_time.seconds >= ApiConstants.EXIT_GAME_TIME or not game_tools.ready_to_play(game, player)) and player.isPlaying:
                        game_tools.exitPlayer(game,player,players,len(players))
                    elif (diff_time.seconds >= ApiConstants.AUTO_EXIT_GAME):
                        game_tools.exitPlayer(game,player,players,len(players))
                
                game.refresh_from_db()
                if game.status == 'wt' and len(players)<2:
                    game.starter=-1
                    game.board = ""
                    game.save()

    finally:
        connection.close()  # Cierra conexiones a la DB.
        import gc
        gc.collect()  # Fuerza liberación de memoria.

        
def automaticCoupleStarter(game):
    next = game.next_player
    patner = (next+2)%4
    starter = game.starter
    lastMoveTime = lastMove(game)
    time_diff1 = timezone.now() - lastMoveTime
    logger_api.info("Entro a automaticCouple")
    logger_api.info("La diferencia de tiempo es "+ str(time_diff1.seconds))
    if time_diff1.seconds > ApiConstants.AUTO_WAIT_PATNER and starter == next:
        game_tools.setWinner1(game,next)
    elif time_diff1.seconds > ApiConstants.AUTO_WAIT_WINNER and starter != next:
        game_tools.setWinnerStarterNext1(game,patner,patner,patner)
    game.save()         

def automaticMove(game,players):
    next = game.next_player
    player_w = players[next]
    MOVE_TILE_TIME = game.moveTime
    time_diff = timezone.now() - lastMove(game)
    if len(game.board) == 0:
        tile = game_tools.takeRandomTile(player_w.tiles)
        if time_diff.seconds > (MOVE_TILE_TIME+ApiConstants.AUTO_MOVE_WAIT):
            try:
                # with transaction.atomic():
                error = game_tools.movement(game.id,player_w,players,tile,automatic=True)
                if error is not None:
                    logger.error(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, message: {error})")
                game_tools.updateLastPlayerTime(game,player_w.alias)  
                # game_tools.move1(game.id,player_w.alias,tile)
            except Exception as e:
                logger.critical(f"Error critico en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")            
            # game_tools.updateLastPlayerTime(game,player_w.alias)
    else:
        tile = game_tools.takeRandomCorrectTile(player_w.tiles,game.leftValue,game.rightValue)
        if game_tools.isPass(tile):
            if time_diff.seconds > ApiConstants.AUTO_PASS_WAIT:
                try:
                    # with transaction.atomic():
                    error = game_tools.movement(game.id,player_w,players,tile,automatic=True)
                    if error is not None:
                        logger.error(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, error: {str(error)}")
                    game_tools.updateLastPlayerTime(game,player_w.alias)  
                    # game_tools.move1(game.id,player_w.alias,tile)
                except Exception as e:
                    logger.critical(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")
                # game_tools.movement(game,player_w,players,tile)
                # game_tools.updateLastPlayerTime(game,player_w.alias) 
        elif time_diff.seconds > (MOVE_TILE_TIME+ApiConstants.AUTO_MOVE_WAIT):
            try:
                # with transaction.atomic():
                error = game_tools.movement(game.id,player_w,players,tile,automatic=True)
                if error is not None:
                    logger.error(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, message: {error})")
                game_tools.updateLastPlayerTime(game,player_w.alias)  
                # game_tools.move1(game.id,player_w.alias,tile)
            except Exception as e:
                logger.error(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")
            # game_tools.movement(game,player_w,players,tile)
            # game_tools.updateLastPlayerTime(game,player_w.alias)        
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
    if time_diff.seconds > ApiConstants.AUTO_START_WAIT:
        game_tools.startGame1(game.id,players)
