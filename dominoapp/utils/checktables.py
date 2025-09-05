import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from dominoapp.utils import game_tools
from dominoapp.models import DominoGame, DataGame, Player
from django.utils import timezone
from django.db import connection
from dominoapp.utils.constants import ApiConstants
import logging
logger = logging.getLogger('django')
logger_api = logging.getLogger(__name__)

def automatic_move_in_game():
    try:
        logger_api.info(f"Automatic Move Tile")
                
        datas = DataGame.objects.filter(player1__isnull=False, active=True).select_related(
            'player1',  # Precarga player1
            'player2',  # Precarga player2
            'player3',  # Precarga player3
            'player4'   # Precarga player4
        ).iterator()
        
        for data_game in datas:
            game = data_game.match.domino_game
            players = game_tools.playersCount(data_game)
            players_running = list(filter(lambda p: p.isPlaying, players))
            if data_game and game.status == 'ru':
                possibleStarter = (game.inPairs and game.startWinner and (data_game is not None and data_game.winner >= 4))
                if possibleStarter:
                    logger_api.info('Esperando al salidor')
                    try:
                        automaticCoupleStarter(data_game)
                    except Exception as e:
                        logger.critical(f'Ocurrio una excepcion escogiendo el salidor en el juego {str(game.id)}, error: {str(e)}')        
                else:
                    try:
                        automaticMove(data_game,players_running)
                    except Exception as e:
                        logger.critical(f'Ocurrio una excepcion moviendo una ficha en el juego {str(game.id)},\n Data:(player_index: {data_game.next_player}, players_in: {len(players_running)} ),\n error: {str(e)}')    
            elif data_game and (game.status == 'fg' and game.perPoints == False) or game.status == 'fi':
                try:
                    restargame = True
                    if game.status == 'fg':
                        for player in players_running:
                            diff_time = timezone.now() - player.lastTimeInSystem
                            if (diff_time.seconds >= ApiConstants.EXIT_GAME_TIME or not game_tools.ready_to_play(game,player)) and player.isPlaying:
                                game_tools.exitPlayer(data_game,player,players,len(players))
                                data_game = DataGame.objects.filter(match__domino_game__id=game.id, active=True).order_by('-id').first()
                                players = game_tools.playersCount(data_game)
                        if len(players)<2:
                            restargame = False
                    if restargame:
                        automaticStart(data_game,players)
                except Exception as e:
                    logger.critical(f'Ocurrio una excepcion comenzando el juego en la mesa {str(game.id)}, error: {str(e)}')    
            elif data_game and game.status == 'fg' or game.status == 'wt' or game.status == 'ready':
                for player in players:
                    diff_time = timezone.now() - player.lastTimeInSystem
                    if (diff_time.seconds >= ApiConstants.EXIT_GAME_TIME or not game_tools.ready_to_play(game, player)) and player.isPlaying:
                        exit = game_tools.exitPlayer(data_game,player,players,len(players))
                        if exit:
                            data_game = DataGame.objects.filter(active=True, match__domino_game__id=game.id).order_by('-id').first()
                            players = game_tools.playersCount(data_game)
                    elif (diff_time.seconds >= ApiConstants.AUTO_EXIT_GAME):
                        exit = game_tools.exitPlayer(data_game,player,players,len(players))
                        if exit:
                            data_game = DataGame.objects.filter(active=True, match__domino_game__id=game.id).order_by('-id').first()
                            players = game_tools.playersCount(data_game)
                
                # game.refresh_from_db()
                    
                # if game.status == 'wt' and len(players)<2:
                #     # game.starter=-1
                #     # game.board = ""
                #     game.save()

    finally:
        connection.close()  # Cierra conexiones a la DB.
        import gc
        gc.collect()  # Fuerza liberación de memoria.

        
def automaticCoupleStarter(data_game:DataGame):
    next = data_game.next_player
    patner = (next+2)%4
    starter = data_game.starter
    lastMoveTime = lastMove(data_game)
    time_diff1 = timezone.now() - lastMoveTime
    logger_api.info("Entro a automaticCouple")
    logger_api.info("La diferencia de tiempo es "+ str(time_diff1.seconds))
    if time_diff1.seconds > ApiConstants.AUTO_WAIT_PATNER and starter == next:
        game_tools.setWinner1(data_game,next)
    elif time_diff1.seconds > ApiConstants.AUTO_WAIT_WINNER and starter != next:
        game_tools.setWinnerStarterNext1(data_game,patner,patner,patner)
    data_game.save()         

def automaticMove(data_game: DataGame,players:list[Player]):
    game=data_game.match.domino_game
    next = data_game.next_player
    player_w = players[next]
    MOVE_TILE_TIME = game.moveTime
    time_diff = timezone.now() - lastMove(data_game)
    if len(data_game.board) == 0:
        tile = game_tools.takeRandomTile(player_w.tiles)
        if time_diff.seconds > (MOVE_TILE_TIME+ApiConstants.AUTO_MOVE_WAIT):
            try:
                error = game_tools.movement(game.id,player_w,players,tile,automatic=True)
                if error is not None:
                    logger.error(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, message: {error})")
                game_tools.updateLastPlayerTime(data_game,player_w.alias)  
            except Exception as e:
                logger.critical(f"Error critico en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")            

    else:
        tile = game_tools.takeRandomCorrectTile(player_w.tiles,data_game.leftValue,data_game.rightValue)
        if game_tools.isPass(tile):
            if time_diff.seconds > ApiConstants.AUTO_PASS_WAIT:
                try:
                    error = game_tools.movement(game.id,player_w,players,tile,automatic=True)
                    if error is not None:
                        logger.error(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, error: {str(error)}")
                    game_tools.updateLastPlayerTime(data_game,player_w.alias)  
                    
                except Exception as e:
                    logger.critical(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")
                
        elif time_diff.seconds > (MOVE_TILE_TIME+ApiConstants.AUTO_MOVE_WAIT):
            try:
                error = game_tools.movement(game.id,player_w,players,tile,automatic=True)
                if error is not None:
                    logger.error(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, message: {error})")
                game_tools.updateLastPlayerTime(data_game,player_w.alias)  
                
            except Exception as e:
                logger.error(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")
            

def lastMove(data_game:DataGame):
    res = data_game.start_time
    if data_game.lastTime1 is not None and data_game.lastTime1 > res:
        res = data_game.lastTime1
    if data_game.lastTime2 is not None and data_game.lastTime2 > res:
        res = data_game.lastTime2
    if data_game.lastTime3 is not None and data_game.lastTime3 > res:
        res = data_game.lastTime3
    if data_game.lastTime4 is not None and data_game.lastTime4 > res:
        res = data_game.lastTime4
    return res                

def automaticStart(data_game:DataGame,players:list[Player]):
    lastMoveTime = lastMove(data_game)
    time_diff = timezone.now() - lastMoveTime
    if time_diff.seconds > ApiConstants.AUTO_START_WAIT:
        game_tools.startGame1(data_game.match.domino_game.id,players)
