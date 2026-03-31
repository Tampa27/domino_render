from rest_framework.response import Response
from dominoapp.models import Player, SummaryPlayer, DominoGame, MoveRegister,Bank, Match_Game
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import DatabaseError
from django.db.models import F
import random
from django.db import transaction
import logging
from dominoapp.utils.transactions import create_game_transactions
from dominoapp.connectors.pusher_connector import PushNotificationConnector
from dominoapp.utils.constants import ApiConstants
from dominoapp.utils.cache_tools import update_player_presence_cache
from dominoapp.utils.move_register_utils import movement_register
from dominoapp.utils.players_tools import update_elo_pair, update_elo, get_summary_model

logger = logging.getLogger(__name__)
logger_discord = logging.getLogger('django')


def setWinner1(game: DominoGame, winner: int):
    game.winner = winner
    game.start_time = timezone.now()

def setWinnerStarterNext1(game: DominoGame, winner: int, starter: int, next_player: int):
    game.starter = starter
    game.winner = winner
    game.next_player = next_player
    game.start_time = timezone.now()

def checkPlayerJoined(player: Player,game: DominoGame) -> tuple[bool, list[Player]]:
    res = False
    players = []
    if game.player1 is not None:
        players.append(game.player1)
        if game.player1.alias == player.alias:
            res = True
    if game.player2 is not None:
        players.append(game.player2)
        if game.player2.alias == player.alias:
            res = True
    if game.player3 is not None:
        players.append(game.player3)
        if game.player3.alias == player.alias:
            res = True
    if game.player4 is not None:
        players.append(game.player4)
        if game.player4.alias == player.alias:
            res = True
    return res,players

def startGame1(game:DominoGame,players:list[Player]):
    n = len(players)
    if game.starter == -1 or game.starter >= n:
        game.next_player = random.randint(0,n-1)
        game.starter = game.next_player
    else:
        # if players[game.starter].alias != players_ru[game.starter].alias:
        #     game.starter = getPlayerIndex(players_ru,players[game.starter])
        game.next_player = game.starter
    if game.inPairs and game.winner != DominoGame.Tie_Game:
        if game.starter == 0 or game.starter == 2:
            game.winner = DominoGame.Winner_Couple_1
        else:
            game.winner = DominoGame.Winner_Couple_2    
    
    try:
        bank = Bank.objects.all().first()
    except:
        bank = Bank.objects.create()
    
    bank.data_played+=1

    game.board = ''
    if game.perPoints and (game.status =="ready" or game.status =="fg"):
        game.scoreTeam1 = 0
        game.scoreTeam2 = 0
        for player in players:
            player.points = 0
        game.rounds = 0

        bank.game_played+=1
    elif not game.perPoints:
        bank.game_played+=1
    
    bank.save(update_fields=['game_played', 'data_played'])

    shuffle(game,players)          
    game.status = "ru"
    game.start_time = timezone.now()
    game.leftValue = -1
    game.rightValue = -1
    game.lastTime1 = timezone.now()
    game.lastTime2 = timezone.now()
    game.lastTime3 = timezone.now()
    game.lastTime4 = timezone.now()
    game.save(update_fields=['board','status','start_time','leftValue','rightValue','lastTime1','lastTime2','lastTime3','lastTime4', 'next_player','starter','winner','scoreTeam1','scoreTeam2','rounds'])

### Si todo sale bien se borra este que es viejo
def movement_old(game:DominoGame,player:Player,players:list,tile:str, automatic=False):
    n = len(players)
    w = getPlayerIndex(players,player)
    passTile = isPass(tile)
    
    if isMyTurn(game.board,w,game.starter,n, game.next_player) == False:
        logger.warning(f"{player.alias} intento mover {tile} pero se detecto que no es su turno. Esta en la posicion: {w} y le toca el turno al player: {game.next_player}. El salidor es {game.starter}")
        return(f"{player.alias} intento mover {tile} pero se detecto que no es su turno. Esta en la posicion: {w} y le toca el turno al player: {game.next_player}. El salidor es {game.starter}")
    if noCorrect(game,tile):
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que no es una ficha correcta")
        return(f"{player.alias} intento mover {tile} pero se detecto que no es una ficha correcta")
    if (passTile and (game.status == 'fi' or game.status == 'fg')):
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que el juego habia terminado")
        return(f"{player.alias} intento mover {tile} pero se detecto que el juego habia terminado")
    if (len(game.board) == 0 and passTile):
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que el juego habia empezado")
        return(f"{player.alias} intento mover {tile} pero se detecto que el juego habia empezado")
    if CheckPlayerTile(tile, player) == False:
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que la ficha no le pertenese")
        return(f"{player.alias} intento mover {tile} pero se detecto que la ficha no le pertenese")
    if not CorrectPassTile(game,player,tile):
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que tenia fichas para jugar")
        return(f"{player.alias} intento pasarse con fichas")
    
    try:
        bank = Bank.objects.all().first()
    except:
        bank = Bank.objects.create()

    if passTile == False:
        isCapicua = False
        if game.perPoints:
            isCapicua = checkCapicua(game,tile)
        
        move_register = movement_register(game, player, tile, players, automatic) 
        updateSides(game,tile)
        tiles_count,tiles = updateTiles(player,tile)
        player.tiles = tiles
        player.save(update_fields=['tiles'])
        if tiles_count == 0:
            game.status = 'fg'
            game.start_time = timezone.now()
            if game.startWinner:
                game.starter = w
                game.next_player = w
            else:
                starter_next = (game.starter+1)%n
                game.next_player = starter_next
                game.starter = starter_next
            game.winner = w
            if game.perPoints:
                game.rounds+=1
                if game.in_tournament:
                    match = Match_Game.objects.get(game__id = game.id)
                    match.count_game += 1
                    match.save(update_fields=["count_game"])
                updateAllPoints(game,players,w,move_register,isCapicua)
            else:
                updatePlayersData(game,players,w,"fg",move_register, bank)
                if game.inPairs:
                    if w == DominoGame.Winner_Player_1 or w == DominoGame.Winner_Player_3:
                        game.winner = DominoGame.Winner_Couple_1
                    elif w == DominoGame.Winner_Player_2 or w == DominoGame.Winner_Player_4:
                        game.winner = DominoGame.Winner_Couple_2
        else:
            game.next_player = (w+1) % n 
    elif checkClosedGame1(game,n):
        move_register = movement_register(game, player, tile, players, automatic)
        winner = getWinner(players,game.inPairs,game.variant)
        game.status = 'fg'
        game.start_time = timezone.now()
        game.winner = winner
        if game.perPoints:
            game.rounds+=1
            if game.in_tournament:
                match = Match_Game.objects.get(game__id = game.id)
                match.count_game += 1
                match.save(update_fields=["count_game"])
        if winner < DominoGame.Tie_Game:
            if game.startWinner:
                game.starter = winner
                game.next_player = winner
            else:
                starter_next = (game.starter+1)%n
                game.next_player = starter_next
                game.starter = starter_next                    
        if game.perPoints and winner < DominoGame.Tie_Game:
            updateAllPoints(game,players,winner,move_register)
        elif game.perPoints and winner == DominoGame.Tie_Game:
            game.status = "fi"
            if game.startWinner and (game.lostStartInTie != True or game.inPairs == False):
                game.next_player = game.starter
            else:    
                game.starter = (game.starter+1)%n
                game.next_player = game.starter
        else:
            updatePlayersData(game,players,winner,"fg",move_register, bank)
            if game.inPairs and winner < DominoGame.Tie_Game:
                if winner == DominoGame.Winner_Player_1 or winner == DominoGame.Winner_Player_3:
                    game.winner = DominoGame.Winner_Couple_1
                elif winner == DominoGame.Winner_Player_2 or winner == DominoGame.Winner_Player_4:
                    game.winner = DominoGame.Winner_Couple_2                
        if winner == DominoGame.Tie_Game:
            for player in players:
                summary = get_summary_model(player)
                summary.data_tie +=1 
                summary.save(update_fields=['data_tie'])
    else:
        move_register = movement_register(game, player, tile, players, automatic)
        updatePassCoins(w,game,players, move_register)
        game.next_player = (w+1) % n
    
    if game.status == "fg":
        bank.data_completed+=1
        bank.game_completed+=1
        
        for player in players:
            summary = get_summary_model(player)
            if game.variant == 'd6':
                summary.play_66_game += 1
            else:
                summary.play_99_game += 1
            if game.inPairs:
                summary.play_in_pairs += 1
            else:
                summary.play_in_single += 1
            if game.perPoints:
                summary.play_by_points += 1
            else:
                summary.play_without_points += 1
            summary.save(update_fields=['play_66_game','play_99_game','play_in_pairs','play_in_single','play_by_points','play_without_points'])            
    elif game.status == "fi":
        bank.data_completed+=1
    
    bank.save(update_fields=["data_completed","game_completed", "game_coins"])

    game.board += (tile+',')
    game.save(update_fields=['board','status','next_player','starter','winner','leftValue','rightValue','rounds','start_time', 'scoreTeam1', 'scoreTeam2'])
    logger.info(player.alias+" movio "+tile)
    
    ## Comento las Push pq no se estan usando y se demoran en responder, si se quieren usar hay que optimizar el proceso de envio de notificaciones
    # PushNotificationConnector.push_notification(
    #         channel=f'mesa_{game.id}',
    #         event_name='move_tile',
    #         data_notification={
    #             'game_status': game.status,
    #             'player': player.id,
    #             'tile': tile,
    #             'next_player': game.next_player,
    #             'time': timezone.now().strftime("%d/%m/%Y, %H:%M:%S")
    #         }
    #     )
    
    return None
###################################################################

def movement(game: DominoGame, player: Player, players: list[Player], tile: str, automatic=False):
    n = len(players)
    w = getPlayerIndex(players, player)
    passTile = isPass(tile)
    
    # 1. Validaciones iniciales (Fail Fast)
    error = validate_move(game, player, players, tile, w, passTile)
    if error:
        return error

    # 3. Lógica de Movimiento y Registro
    move_register = movement_register(game, player, tile, players, automatic)
    
    update_bank_coins = 0

    if not passTile:
        isCapicua = False
        if game.perPoints:
            isCapicua = checkCapicua(game, tile)
        
        updateSides(game, tile)
        tiles_count, new_tiles = updateTiles(player, tile)
        player.tiles = new_tiles
        player.save(update_fields=['tiles'])

        if tiles_count == 0:
            handle_game_win(game, players, w, n, move_register, update_bank_coins, isCapicua)
        else:
            game.next_player = (w + 1) % n          
    elif checkClosedGame1(game, n):
        winner = getWinner(players, game.inPairs, game.variant)
        handle_closed_game(game, players, winner, n, move_register, update_bank_coins)
    else:
        # Es un pase normal
        updatePassCoins(w, game, players, move_register)
        game.next_player = (w + 1) % n

    # 4. Guardado final de la mesa (Una sola query)
    game.board += (tile + ',')
    game.save(update_fields=[
        'board', 'status', 'next_player', 'starter', 'winner', 
        'leftValue', 'rightValue', 'rounds', 'start_time', 
        'scoreTeam1', 'scoreTeam2'
    ])

    # 5. Actualización masiva de Summaries (OPTIMIZACIÓN CLAVE)
    # En lugar de .save() dentro de un loop, lo hacemos al final si el juego terminó
    try:
        bank = Bank.objects.all().first()
    except:
        bank = Bank.objects.create()
    
    if game.status in ["fg", "fi"]:
        update_all_summaries(game, players, bank)
    bank.game_coins += update_bank_coins
    bank.save(update_fields=["data_completed","game_completed", "game_coins"])
    
    logger.info(f"{player.alias} movio {tile}")
    return None

#### Adicionales para limpieza en el movement ####
def validate_move(game: DominoGame, player: Player, players: list[Player], tile:str, w:int, passTile: bool):
    """Valida el movimiento de un jugador. """
    n = len(players)
    if isMyTurn(game.board,w,game.starter,n, game.next_player) == False:
        logger.warning(f"{player.alias} intento mover {tile} pero se detecto que no es su turno. Esta en la posicion: {w} y le toca el turno al player: {game.next_player}. El salidor es {game.starter}")
        return(f"{player.alias} intento mover {tile} pero se detecto que no es su turno. Esta en la posicion: {w} y le toca el turno al player: {game.next_player}. El salidor es {game.starter}")
    if noCorrect(game,tile):
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que no es una ficha correcta")
        return(f"{player.alias} intento mover {tile} pero se detecto que no es una ficha correcta")
    if (passTile and (game.status == 'fi' or game.status == 'fg')):
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que el juego habia terminado")
        return(f"{player.alias} intento mover {tile} pero se detecto que el juego habia terminado")
    if (len(game.board) == 0 and passTile):
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que el juego habia empezado")
        return(f"{player.alias} intento mover {tile} pero se detecto que el juego habia empezado")
    if CheckPlayerTile(tile, player) == False:
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que la ficha no le pertenese")
        return(f"{player.alias} intento mover {tile} pero se detecto que la ficha no le pertenese")
    if not CorrectPassTile(game,player,tile):
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que tenia fichas para jugar")
        return(f"{player.alias} intento pasarse con fichas")
    
    return None

def update_all_summaries(game: DominoGame, players: list[Player], bank: Bank):
    """Actualiza estadísticas de todos los jugadores y el banco en bloque."""
    player_ids = [p.id for p in players]
    
    # Actualización del Banco
    if game.status == "fg":
        bank.data_completed += 1
        bank.game_completed += 1
    elif game.status == "fi":
        bank.data_completed += 1

    # Actualización masiva de Summaries usando F() para evitar bloqueos
    
    filter_params = {'player_id__in': player_ids}

    if game.status == "fg":
        field_variant = 'play_66_game' if game.variant == 'd6' else 'play_99_game'
        field_pair = 'play_in_pairs' if game.inPairs else 'play_in_single'
        field_points = 'play_by_points' if game.perPoints else 'play_without_points'
        
        SummaryPlayer.objects.filter(**filter_params).update(
            **{field_variant: F(field_variant) + 1},
            **{field_pair: F(field_pair) + 1},
            **{field_points: F(field_points) + 1}
        )
    
    if game.winner == DominoGame.Tie_Game:
        SummaryPlayer.objects.filter(**filter_params).update(data_tie=F('data_tie') + 1)

def handle_game_win(game: DominoGame, players: list[Player], winner_idx: int, n: int, move_register: MoveRegister, update_bank_coins: int, isCapicua: bool):
    """Maneja la victoria por quedarse sin fichas."""
    game.status = 'fg'
    game.start_time = timezone.now()
    game.winner = winner_idx

    # Lógica de rotación de salida (Starter)
    if game.startWinner:
        game.starter = winner_idx
        game.next_player = winner_idx
    else:
        game.starter = (game.starter + 1) % n
        game.next_player = game.starter

    if game.perPoints:
        game.rounds += 1
        # Actualización atómica de Match_Game si aplica
        if game.in_tournament:
            Match_Game.objects.filter(game__id=game.id).update(count_game=F('count_game') + 1)
        
        # Llamamos a la función de puntos que optimizamos antes
        updateAllPoints(game, players, winner_idx, move_register, update_bank_coins, isCapicua)
    else:
        # Si no es por puntos, solo actualizamos los datos básicos
        updatePlayersData(game, players, winner_idx, "fg", move_register, update_bank_coins)
        
        # Mapeo de ganador a pareja si es necesario
        if game.inPairs:
            if winner_idx in [0, 2]:
                game.winner = DominoGame.Winner_Couple_1
            else:
                game.winner = DominoGame.Winner_Couple_2

def handle_closed_game(game: DominoGame, players: list[Player], winner: int, n: int, move_register: MoveRegister, update_bank_coins: int):
    """Maneja la lógica cuando el juego se cierra/tranca."""
    game.status = 'fg'
    game.start_time = timezone.now()
    game.winner = winner

    if winner < DominoGame.Tie_Game: # Alguien ganó   
        # Rotación de salida
        if game.startWinner:
            game.starter = winner
            game.next_player = winner
        else:
            game.starter = (game.starter + 1) % n
            game.next_player = game.starter        

    if game.perPoints:
        game.rounds += 1
        if game.in_tournament:
            Match_Game.objects.filter(game__id=game.id).update(count_game=F('count_game') + 1)
            
        if winner < DominoGame.Tie_Game: # Alguien ganó por puntos            
            updateAllPoints(game, players, winner, move_register, update_bank_coins) 
        elif winner == DominoGame.Tie_Game: # Empate técnico
            game.status = "fi" # El juego sigue o se repite la mano según tu regla
            # Lógica de quién sale en el empate
            if not (game.startWinner and (game.lostStartInTie != True or game.inPairs == False)):
                game.starter = (game.starter + 1) % n
            game.next_player = game.starter
    else:
        # Juego cerrado sin puntos
        updatePlayersData(game, players, winner, "fg", move_register, update_bank_coins)
        if game.inPairs and winner < DominoGame.Tie_Game:
            game.winner = DominoGame.Winner_Couple_1 if winner in [0, 2] else DominoGame.Winner_Couple_2

#################################################################
def CheckPlayerTile(tile:str, player:Player):
    if isPass(tile):        
        return True
    tiles = player.tiles.split(',')
    inverse = rTile(tile)
    if tile in tiles or inverse in tiles:
        return True
    return False

def CorrectPassTile(game: DominoGame, player:Player, tile:str):
    tiles = player.tiles.split(',')
    if isPass(tile):        
        numbers = [int(side) for single in tiles for side in single.split('|')]
        if game.leftValue in numbers or game.rightValue in numbers:
            # Comprobar que realmente no lleva fichas
            return False
    return True 

def noCorrect(game,tile):
    values = tile.split('|')
    val0 = int(values[0])
    if val0 == -1 or (game.leftValue == -1 and game.rightValue == -1):
        return False
    if game.leftValue == val0 or game.rightValue == val0:
        return False
    return True

def rTile(tile)->str:
    values = tile.split('|')
    return (values[1]+"|"+values[0])

### si todo sale bien borrar este que es el viejo
def updatePlayersData_old(game:DominoGame,players:list[Player],w:int,status:str,move_register: MoveRegister):
    try:
        bank = Bank.objects.all().first()
    except ObjectDoesNotExist:
        bank = Bank.objects.create()
    bank_coins = 0
    n_p = 0
    n = len(players)
    for i in range(n):
        if players[i].isPlaying == True:
            n_p+=1
    if game.inPairs:
        for i in range(n):
            summary = get_summary_model(players[i])
            if (i == w or i == ((w+2)%4)) and w < 4:
                summary.data_wins += 1
                summary.save(update_fields=['data_wins'])
                if game.payWinValue > 0:
                    bank_coins = int(game.payWinValue*ApiConstants.DISCOUNT_PERCENT/100)
                    player_coins = (game.payWinValue-bank_coins)
                    bank.game_coins+=(bank_coins)
                    players[i].earned_coins+= player_coins
                    summary.earned_coins+= player_coins
                    summary.save(update_fields=['earned_coins'])
                    create_game_transactions(
                        game=game,to_user=players[i], amount=player_coins, status="cp", 
                        descriptions=f"gane en el juego {game.id}",
                        move_register=move_register)
                if status == "fg" and game.perPoints:
                    summary.match_wins += 1
                    summary.save(update_fields=['match_wins'])
                    if game.payMatchValue > 0:
                        bank_coins = int(game.payMatchValue*ApiConstants.DISCOUNT_PERCENT/100)
                        bank.game_coins+=bank_coins
                        player_coins = (game.payMatchValue-bank_coins)
                        players[i].earned_coins+= player_coins
                        create_game_transactions(
                            game=game, to_user=players[i], amount=player_coins, status="cp", 
                            descriptions=f"gane en el juego {game.id}",
                            move_register=move_register)
                players[i].save(update_fields=['earned_coins'])
            else:
                summary.data_loss += 1
                summary.save(update_fields=['data_loss'])
                if game.payWinValue > 0 and w != 4:
                    players[i].earned_coins-=game.payWinValue
                    if players[i].earned_coins<0:
                        players[i].recharged_coins += players[i].earned_coins
                        players[i].earned_coins = 0
                    summary.loss_coins+=game.payWinValue
                    summary.save(update_fields=['loss_coins'])
                    create_game_transactions(
                        game=game, from_user=players[i], amount=game.payWinValue, status="cp", 
                        descriptions=f"perdi en el juego {game.id}",
                        move_register=move_register)
                if status == "fg" and game.perPoints:
                    summary.match_loss += 1
                    summary.save(update_fields=['match_loss'])
                    if game.payMatchValue > 0 and w != 4:
                        players[i].earned_coins-=game.payMatchValue
                        if players[i].earned_coins<0:
                            players[i].recharged_coins += players[i].earned_coins
                            players[i].earned_coins = 0
                        summary.loss_coins+=game.payMatchValue
                        summary.save(update_fields=['loss_coins'])
                        create_game_transactions(
                            game=game, from_user=players[i], amount=game.payMatchValue, status="cp", 
                            descriptions=f"perdi en el juego {game.id}",
                            move_register=move_register)
                players[i].save(update_fields=['earned_coins','recharged_coins'])
        if game.status == "fg":
            try:
                if w<4:
                    update_elo_pair([players[w],players[((w+2)%4)]],[players[(((w+1)+2)%4)],players[(((w+3)+2)%4)]])
                else:
                    update_elo_pair([players[0],players[2]],[players[1],players[3]],True)
            except Exception as error:
                try:
                    logger_discord.error(f"Error actualizando los ELOS por pareja, pair1: [{[players[w],players[((w+2)%4)]]}], pair2:{[players[(((w+1)+2)%4)],players[(((w+3)+2)%4)]]}, Detalles del Error: {error}")
                except:
                    logger_discord.critical(f"Error en actualizar los ElOS por pareja y al capturar el error, players: {players}, winner: {w}")
    else:
        for i in range(n):
            summary = get_summary_model(players[i])
            if i == w:
                summary.data_wins += 1
                summary.save(update_fields=['data_wins'])

                if game.payWinValue > 0:
                    bank_coins = int(game.payWinValue*(n_p-1)*ApiConstants.DISCOUNT_PERCENT/100)
                    bank.game_coins+=bank_coins
                    player_coins = (game.payWinValue*(n_p-1)-bank_coins)
                    players[i].earned_coins+= player_coins
                    summary.earned_coins += player_coins
                    summary.save(update_fields=['earned_coins'])
                    create_game_transactions(
                        game=game, to_user=players[i], amount=player_coins, status="cp", 
                        descriptions=f"gane en el juego {game.id}",
                        move_register=move_register)
                if status == "fg" and game.perPoints:
                    summary.match_wins += 1
                    summary.save(update_fields=['match_wins'])
                    if game.payMatchValue > 0:
                        bank_coins = int(game.payMatchValue*(n_p-1)*ApiConstants.DISCOUNT_PERCENT/100)
                        bank.game_coins+=bank_coins
                        player_coins = (game.payMatchValue*(n_p-1)-bank_coins)
                        players[i].earned_coins+= player_coins
                        summary.earned_coins += player_coins
                        summary.save(update_fields=['earned_coins'])
                        create_game_transactions(
                            game=game, to_user=players[i], amount=player_coins, status="cp", 
                            descriptions=f"gane en el juego {game.id}",
                            move_register=move_register)
                players[i].save(update_fields=['earned_coins'])
            elif players[i].isPlaying == True and w < 4:
                summary.data_loss += 1
                summary.save(update_fields=['data_loss'])
                if game.payWinValue > 0:
                    players[i].earned_coins-=game.payWinValue
                    if players[i].earned_coins<0:
                            players[i].recharged_coins += players[i].earned_coins
                            players[i].earned_coins = 0
                    summary.loss_coins+=game.payWinValue
                    summary.save(update_fields=['loss_coins'])
                    create_game_transactions(
                        game=game, from_user=players[i], amount=game.payWinValue, status="cp", 
                        descriptions=f"perdi en el juego {game.id}",
                        move_register=move_register)
                if status == "fg" and game.perPoints:
                    summary.match_loss += 1
                    summary.save(update_fields=['match_loss'])
                    if game.payMatchValue > 0 and w != 4:
                        players[i].earned_coins-=game.payMatchValue
                        if players[i].earned_coins<0:
                            players[i].recharged_coins += players[i].earned_coins
                            players[i].earned_coins = 0
                        summary.loss_coins+=game.payMatchValue
                        summary.save(update_fields=['loss_coins'])
                        create_game_transactions(
                            game=game, from_user=players[i], amount=game.payMatchValue, status="cp", 
                            descriptions=f"perdi en el juego {game.id}",
                            move_register=move_register)
                players[i].save(update_fields=['earned_coins','recharged_coins'])                                    
        if game.status == "fg":
            try:
                update_elo(players,(players[w] if w < 4 else None))
            except Exception as error:
                try:
                    player_alias_list = [f'{player.alias}, ' for player in players]
                    logger_discord.error(f"Error actualizando los ELOS individuales en el game: {game.id}, players: [{player_alias_list}], winner:{players[w].alias if w < len(players) else f'INVALID_INDEX: {w}'}, Detalles del Error: {error}")
                except:
                    logger_discord.critical(f"Error en actualizar los ElOS individuales y al capturar el error, players: {players}, winner: {w}")
    bank.save(update_fields=['game_coins'])
#############################################################

def updatePlayersData(game: DominoGame, players: list[Player], w: int, status: str, move_register: MoveRegister, update_bank_coins: int):
    
    n = len(players)
    playing_count = sum(1 for p in players if p.isPlaying)
    is_final_game = (status == "fg")
    
    # Listas para guardar cambios y procesar al final
    summaries_to_update = []
    players_to_update = []
    
    # 2. Identificar ganadores según el modo
    winners_idx = []
    if game.inPairs:
        if w < 4: winners_idx = [w, (w + 2) % 4]
    else:
        if w < n: winners_idx = [w]

    # 3. Bucle único de cálculo (CPU es más barato que DB)
    for i in range(n):
        player = players[i]
        if not player: continue
        
        summary = get_summary_model(player)
        is_winner = i in winners_idx
        
        # Valores de pago
        win_val = game.payWinValue
        match_val = game.payMatchValue if (is_final_game and game.perPoints) else 0
        
        if is_winner:
            # Lógica Ganador
            summary.data_wins += 1
            if is_final_game and game.perPoints:
                summary.match_wins += 1
            
            # Cálculo de monedas (Individual vs Parejas)
            multiplier = (playing_count - 1) if not game.inPairs else 1
            total_win = (win_val * multiplier) + (match_val * multiplier)
            
            if total_win > 0:
                fee_percent = ApiConstants.DISCOUNT_PERCENT / 100
                bank_fee = int(total_win * fee_percent)
                player_net = total_win - bank_fee
                
                update_bank_coins += bank_fee
                player.earned_coins += player_net
                summary.earned_coins += player_net
                
                # Transacción única por premio total
                create_game_transactions(game=game, to_user=player, amount=player_net, 
                                         status="cp", descriptions=f"Gané game {game.id}", 
                                         move_register=move_register)
        else:
            # Lógica Perdedor (Solo si el ganador es válido w < 4)
            if w < 4 and player.isPlaying:
                summary.data_loss += 1
                if is_final_game and game.perPoints:
                    summary.match_loss += 1
                
                total_loss = win_val + match_val
                if total_loss > 0:
                    player.earned_coins -= total_loss
                    if player.earned_coins < 0:
                        player.recharged_coins += player.earned_coins
                        player.earned_coins = 0
                    
                    summary.loss_coins += total_loss
                    create_game_transactions(game=game, from_user=player, amount=total_loss, 
                                             status="cp", descriptions=f"Perdí game {game.id}", 
                                             move_register=move_register)

        # Añadir a colas de guardado
        summaries_to_update.append(summary)
        players_to_update.append(player)

    # 4. PERSISTENCIA MASIVA (El gran ahorro de tiempo)
    for p in players_to_update:
        p.save(update_fields=['earned_coins', 'recharged_coins'])
    
    for s in summaries_to_update:
        s.save(update_fields=['data_wins', 'data_loss', 'match_wins', 'match_loss', 'earned_coins', 'loss_coins'])
    
    # 5. Actualización de ELO (al final de la transacción)
    if is_final_game:
        try:
            if game.inPairs:
                update_elo_pair([players[0], players[2]], [players[1], players[3]], (w >= 4))
            else:
                update_elo(players, (players[w] if w < 4 else None))
        except Exception as e:
            logger_discord.error(f"Error ELO game {game.id}: {e}")

### si todo sale bien borrar este que es el viejo
def updatePassCoins_old(pos:int,game:DominoGame,players:list[Player],move_register:MoveRegister):
    tiles = game.board.split(',')
    rtiles = reversed(tiles)
    prev = 1
    n = len(players)
    for tile in rtiles:
        if len(tile) > 0:
            if isPass(tile):
                prev+=1
            else:
                if prev == 1 or prev == 3:
                    if (pos - prev) < 0:
                        pos1 = pos + (n-prev)
                        summary_player_pass = get_summary_model(players[pos])
                        summary_player_passed = get_summary_model(players[pos1])
                        if game.payPassValue > 0:
                            loss_coins = game.payPassValue
                            players[pos].earned_coins-=loss_coins
                            if players[pos].earned_coins<0:
                                players[pos].recharged_coins += players[pos].earned_coins
                                players[pos].earned_coins = 0
                            
                            # try:
                            #     bank = Bank.objects.all().first()
                            # except ObjectDoesNotExist:
                            #     bank = Bank.objects.create()
                            # bank_coins = int(loss_coins*ApiConstants.DISCOUNT_PERCENT/100)
                            # bank.game_coins+=bank_coins
                            bank_coins=0
                            
                            coins = loss_coins - bank_coins
                            players[pos1].earned_coins+=coins
                            create_game_transactions(
                                game=game, from_user=players[pos], amount=loss_coins, status="cp", 
                                descriptions=f"{players[pos1].alias} me paso en el juego {game.id}, a {game.leftValue} y a {game.rightValue}",
                                move_register=move_register)
                            create_game_transactions(
                                game=game, to_user=players[pos1], amount=coins, status="cp", 
                                descriptions=f"pase a {players[pos].alias} en el juego {game.id}, a {game.leftValue} y a {game.rightValue}",
                                move_register=move_register)
                            
                            summary_player_pass.loss_coins+=loss_coins
                            summary_player_passed.earned_coins+=coins
                            players[pos].save(update_fields=['earned_coins','recharged_coins'])
                            players[pos1].save(update_fields=['earned_coins'])
                        summary_player_pass.owner_pass += 1
                        summary_player_pass.save(update_fields=['owner_pass','loss_coins'])
                        summary_player_passed.pass_player += 1
                        summary_player_passed.save(update_fields=['pass_player', 'earned_coins'])

                    else:
                        pos1 = pos - prev
                        summary_player_pass = get_summary_model(players[pos])
                        summary_player_passed = get_summary_model(players[pos1])
                        if game.payPassValue > 0:
                            loss_coins = game.payPassValue
                            players[pos].earned_coins-=loss_coins
                            if players[pos].earned_coins<0:
                                players[pos].recharged_coins += players[pos].earned_coins
                                players[pos].earned_coins = 0
                            
                            # try:
                            #     bank = Bank.objects.all().first()
                            # except ObjectDoesNotExist:
                            #     bank = Bank.objects.create()
                            # bank_coins = int(loss_coins*ApiConstants.DISCOUNT_PERCENT/100)
                            # bank.game_coins+=bank_coins
                            bank_coins=0

                            coins = loss_coins - bank_coins
                            players[pos1].earned_coins+=coins
                            create_game_transactions(
                                game=game, from_user=players[pos], amount=loss_coins, status="cp",
                                descriptions=f"{players[pos1].alias} me paso en el juego {game.id}, a {game.leftValue} y a {game.rightValue}",
                                move_register=move_register)
                            create_game_transactions(
                                game=game, to_user=players[pos1], amount=coins, status="cp",
                                descriptions=f"pase a {players[pos].alias} en el juego {game.id}, a {game.leftValue} y a {game.rightValue}",
                                move_register=move_register)
                            summary_player_pass.loss_coins += loss_coins
                            summary_player_passed.earned_coins += coins
                            players[pos].save(update_fields=['earned_coins','recharged_coins'])
                            players[pos1].save(update_fields=['earned_coins'])
                        summary_player_pass.owner_pass += 1
                        summary_player_pass.save(update_fields=['owner_pass','loss_coins'])
                        summary_player_passed.pass_player += 1
                        summary_player_passed.save(update_fields=['pass_player', 'earned_coins'])
                elif prev == 2 and game.inPairs == False:
                    if (pos - 2) < 0:
                        pos1 = pos + (n-prev)
                        summary_player_pass = get_summary_model(players[pos])
                        summary_player_passed = get_summary_model(players[pos1])
                        if game.payPassValue > 0:
                            loss_coins = game.payPassValue
                            players[pos].earned_coins-=loss_coins
                            if players[pos].earned_coins<0:
                                players[pos].recharged_coins += players[pos].earned_coins
                                players[pos].earned_coins = 0
                            
                            # try:
                            #     bank = Bank.objects.all().first()
                            # except ObjectDoesNotExist:
                            #     bank = Bank.objects.create()
                            # bank_coins = int(loss_coins*ApiConstants.DISCOUNT_PERCENT/100)
                            # bank.game_coins+=bank_coins
                            bank_coins=0
                            
                            coins = loss_coins - bank_coins
                            players[pos1].earned_coins+=coins
                            create_game_transactions(
                                game=game, from_user=players[pos], amount=loss_coins, status="cp",
                                descriptions=f"{players[pos1].alias} me paso en el juego {game.id}, a {game.leftValue} y a {game.rightValue}",
                                move_register=move_register)
                            create_game_transactions(
                                game=game, to_user=players[pos1], amount=coins, status="cp",
                                descriptions=f"pase a {players[pos].alias} en el juego {game.id}, a {game.leftValue} y a {game.rightValue}",
                                move_register=move_register)
                            summary_player_pass.loss_coins += loss_coins
                            summary_player_passed.earned_coins += coins
                            players[pos].save(update_fields=['earned_coins','recharged_coins'])
                            players[pos1].save(update_fields=['earned_coins'])
                        summary_player_pass.owner_pass += 1
                        summary_player_pass.save(update_fields=['owner_pass','loss_coins'])
                        summary_player_passed.pass_player += 1
                        summary_player_passed.save(update_fields=['pass_player', 'earned_coins'])
                        
                    else:        
                        pos1 = pos - prev
                        summary_player_pass = get_summary_model(players[pos])
                        summary_player_passed = get_summary_model(players[pos1])
                        if game.payPassValue > 0:
                            loss_coins = game.payPassValue
                            players[pos].earned_coins-=loss_coins
                            if players[pos].earned_coins<0:
                                players[pos].recharged_coins += players[pos].earned_coins
                                players[pos].earned_coins = 0
                            
                            # try:
                            #     bank = Bank.objects.all().first()
                            # except ObjectDoesNotExist:
                            #     bank = Bank.objects.create()
                            # bank_coins = int(loss_coins*ApiConstants.DISCOUNT_PERCENT/100)
                            # bank.game_coins+=bank_coins
                            bank_coins=0
                            
                            coins = loss_coins - bank_coins
                            players[pos1].earned_coins+=coins
                            create_game_transactions(
                                game=game, from_user=players[pos], amount=loss_coins, status="cp",
                                descriptions=f"{players[pos1].alias} me paso en el juego {game.id}, a {game.leftValue} y a {game.rightValue}",
                                move_register=move_register)
                            create_game_transactions(
                                game=game, to_user=players[pos1], amount=coins, status="cp",
                                descriptions=f"pase a {players[pos].alias} en el juego {game.id}, a {game.leftValue} y a {game.rightValue}",
                                move_register=move_register)
                            
                            summary_player_pass.loss_coins += loss_coins
                            summary_player_passed.earned_coins += coins
                            players[pos].save(update_fields=['earned_coins','recharged_coins'])
                            players[pos1].save(update_fields=['earned_coins'])
                        summary_player_pass.owner_pass += 1
                        summary_player_pass.save(update_fields=['owner_pass','loss_coins'])
                        summary_player_passed.pass_player += 1
                        summary_player_passed.save(update_fields=['pass_player', 'earned_coins'])
                break
#################################################################

def updatePassCoins(pos: int, game: DominoGame, players: list[Player], move_register: MoveRegister):
    if game.payPassValue <= 0:
        return # Si no hay pago por pase, ahorramos todo el procesamiento

    tiles = game.board.split(',')
    rtiles = reversed(tiles)
    prev = 1
    n = len(players)
    
    pos1 = -1 # Posición del jugador que "dio el pase"

    # 1. Lógica de búsqueda de quién pasó a quién
    for tile in rtiles:
        if not tile: continue
        if isPass(tile):
            prev += 1
        else:
            # Determinamos pos1 basándonos en la distancia (prev)
            if prev in [1, 3] or (prev == 2 and not game.inPairs):
                pos1 = (pos - prev) % n
            break # Encontramos el movimiento anterior, salimos del bucle

    # 2. Si identificamos un pase válido, procesamos en bloque
    if pos1 != -1:
        player_pass = players[pos]       # El que se pasó
        player_passed = players[pos1]    # El que hizo que el otro se pasara
        
        loss_coins = game.payPassValue
        bank_coins = 0 # Mantengo tu lógica de bank_coins=0
        coins_to_receive = loss_coins - bank_coins

        # 3. Actualización de saldos en memoria
        player_pass.earned_coins -= loss_coins
        if player_pass.earned_coins < 0:
            player_pass.recharged_coins += player_pass.earned_coins
            player_pass.earned_coins = 0
        
        player_passed.earned_coins += coins_to_receive

        # 4. Obtener resúmenes (Summary)
        summary_pass = get_summary_model(player_pass)
        summary_passed = get_summary_model(player_passed)

        # Actualización de estadísticas en memoria
        summary_pass.loss_coins += loss_coins
        summary_pass.owner_pass += 1
        summary_passed.earned_coins += coins_to_receive
        summary_passed.pass_player += 1

        # 5. PERSISTENCIA ÚNICA (Aquí es donde ganamos velocidad)
        # Usamos save() una sola vez por objeto con update_fields
        player_pass.save(update_fields=['earned_coins', 'recharged_coins'])
        player_passed.save(update_fields=['earned_coins'])
        summary_pass.save(update_fields=['loss_coins', 'owner_pass'])
        summary_passed.save(update_fields=['earned_coins', 'pass_player'])

        # 6. Transacciones (Ojalá pudieras hacer esto asíncrono)
        descriptions_pass = f"{player_passed.alias} me paso en el juego {game.id}, a {game.leftValue} y a {game.rightValue}"
        descriptions_passed = f"pase a {player_pass.alias} en el juego {game.id}, a {game.leftValue} y a {game.rightValue}"
        
        create_game_transactions(game=game, from_user=player_pass, amount=loss_coins, 
                                 status="cp", descriptions=descriptions_pass, move_register=move_register)
        create_game_transactions(game=game, to_user=player_passed, amount=coins_to_receive, 
                                 status="cp", descriptions=descriptions_passed, move_register=move_register)

### si todo funciona bien borrar este q es el viejo
def move1_old(game_id: int,player_id: str,tile:str):
    try:
        with transaction.atomic():
            try:
                game = DominoGame.objects.select_for_update(nowait=True).get(id=game_id)
            except DominoGame.DoesNotExist:
                return "Mesa no encontrada."

            # 3. Bloqueamos a los jugadores que YA están sentados de forma independiente
            # Esto evita el error de PostgreSQL
            player_ids = [pid for pid in [game.player1_id, game.player2_id, game.player3_id, game.player4_id] if pid]
            if player_ids:
                # Al hacer list() forzamos la ejecución del select_for_update en la DB
                locked_players = list(Player.objects.select_for_update(nowait=True).filter(id__in=player_ids))

                if len(locked_players) < len(player_ids):
                    # Alguien más está tocando a un jugador, mejor salir y reintentar en 7 seg
                    return "No se pudieron bloquear a todos los jugadores"

            # Al haber usado select_related, estos objetos ya están "bloqueados"
            players = playersCount(game)
            players_ru = list(filter(lambda p: p.isPlaying, players))
            
            # Buscamos al jugador que mueve (ya está bloqueado por el select_for_update de arriba)
            player = next((p for p in players if p.id == player_id), None)
            
            if not player:
                return "Jugador no encontrado en esta partida"
        
            # Ejecutamos la lógica de movimiento
            error = movement(game, player, players_ru, tile)
            
            # Actualizamos tiempos (game.save ya ocurre dentro de movement y aquí)
            updateLastPlayerTime(game, player.alias)
            
            return error

    except DatabaseError:
        # Este error salta si nowait=True detecta que alguien más tiene el candado
        return "La partida está procesando otro movimiento. Intenta de nuevo en un segundo."
        
    except Exception as error:
        logger_discord.error(f"Error en move1, game_id: {game_id}, player_id: {player_id}, error: {error}")
        return "Ocurrió un error al procesar el movimiento."
##################################

def move1(game_id: int, player_request: Player, tile: str):
    start_time = timezone.now()
    try:
        with transaction.atomic():
            # 1. Bloqueamos la mesa y traemos los datos de los jugadores en un JOIN
            try:
                game = DominoGame.objects.select_related(
                    'player1', 'player2', 'player3', 'player4'
                ).select_for_update(of=('self',), nowait=True).get(id=game_id)
            except DominoGame.DoesNotExist:
                return "Mesa no encontrada."

            # 2. Creamos una lista que mantiene EL ORDEN DE LA MESA (para tu lógica)
            # Estos objetos ya vienen con datos por el select_related
            ordered_players_in_table = [game.player1, game.player2, game.player3, game.player4]

            # 3. Extraemos IDs de jugadores existentes para el BLOQUEO
            player_ids = [p.id for p in ordered_players_in_table if p is not None]
            
            # 4. ORDENAMOS LOS IDS SOLO PARA EL SELECT_FOR_UPDATE
            # Esto previene Deadlocks y no afecta a 'game.player1', 'game.player2', etc.
            ids_to_lock = sorted(player_ids)

            # Bloqueamos en la DB usando el orden numérico de ID
            locked_players  = list(Player.objects.select_for_update(nowait=True).filter(id__in=ids_to_lock))
            if len(locked_players) < len(player_ids):
                # Alguien más está tocando a un jugador, mejor salir y reintentar mas tarde
                return "No se pudieron bloquear a todos los jugadores"

            # 5. Buscamos al jugador que realiza el movimiento
            # Lo buscamos en la lista original (la que tiene el orden de la mesa)
            player = next((p for p in ordered_players_in_table if p and p.id == player_request.id), None)
            if not player:
                return "Jugador no encontrado en esta partida"

            # 6. Preparamos la lista de jugadores activos (isPlaying) manteniendo el orden
            players_ru = [p for p in ordered_players_in_table if p and p.isPlaying]
            
            # 7. Ejecutamos la lógica (aquí game.player1, player2, etc. siguen siendo los correctos)
            error = movement(game, player, players_ru, tile)
            
            if error is None:
                # Actualizamos tiempos sin volver a guardar todo el objeto si no es necesario
                updateLastPlayerTime(game, player.alias)
                
                # IMPORTANTE: Solo guardamos los campos que realmente cambian para evitar sobreescribir
                # datos que otros procesos podrían estar tocando.
                game.save(update_fields=[
                    'lastTime1', 'lastTime2', 'lastTime3', 'lastTime4'
                ])

                #### esto hay que cambiarlo a asincrono y pasarcelo a Celery para que no afecte el rendimiento del movimiento, lo mismo con el update_player_presence_cache
                now = timezone.now()
                if player.lastTimeInSystem + timedelta(seconds = 5) < now:
                    player.inactive_player = False
                    player.lastTimeInSystem = now
                    player.lastTimeInGame = now
                    player.save(update_fields=["inactive_player", "lastTimeInSystem" , "lastTimeInGame"])
                    data={
                            'lastTimeInSystem': now,
                            'lastTimeInGame' : now
                        }
                    update_player_presence_cache(player.id, data)
                ###########################################################
            return error

    except DatabaseError as e:
        logger_discord.error(f"Error de DB en move1, Error: {str(e)}, time: {(timezone.now() - start_time).total_seconds()} segundos")
        return "La partida está procesando otro movimiento. Intenta de nuevo."
    except Exception as e:
        logger_discord.critical(f"Error crítico en move1, Error: {str(e)}, time: {(timezone.now() - start_time).total_seconds()} segundos")
        return "Error al procesar el request del movimiento."

def shuffleCouples(game,players):
    random.shuffle(players)
    game.player1 = players[0]
    game.player2 = players[1]
    game.player3 = players[2]
    game.player4 = players[3]

def exitPlayer(game: DominoGame, player: Player, players: list[Player], totalPlayers: int):
    exited = False
    pos = getPlayerIndex(players,player)
    isStarter = (game.starter == pos)
    starter = game.starter
    lastTimeMove = getLastMoveTime(game,player)
    noActivity = False
    if lastTimeMove is not None:
        timediff = timezone.now() - lastTimeMove
        if timediff.seconds >= 60:
            noActivity = True
        
    if game.player1 is not None and game.player1.alias == player.alias:
        game.player1 = None
        exited = True
    elif game.player2 is not None and game.player2.alias == player.alias:
        game.player2 = None
        exited = True        
    elif game.player3 is not None and game.player3.alias == player.alias:
        game.player3 = None
        exited = True
    elif game.player4 is not None and game.player4.alias == player.alias:
        game.player4 = None
        exited = True
    
    if exited:
        player.points = 0
        player.tiles = ""
        if player.isPlaying:
            have_points = havepoints(game)
            if (game.status == "fi" or (game.status == "ru" and (have_points or game.board != ""))) and (game.payWinValue > 0 or game.payMatchValue > 0) and noActivity == False:
                loss_coins = (game.payWinValue+game.payMatchValue)
                coins = loss_coins
                try:
                    bank = Bank.objects.all().first()
                except ObjectDoesNotExist:
                    bank = Bank.objects.create()
                bank_coins = int(coins*ApiConstants.DISCOUNT_PERCENT/100)
                bank.game_coins+=bank_coins
                coins -= bank_coins
                if game.inPairs:
                    coins_value = int(coins/2)
                    players[(pos+1)%4].earned_coins+=coins_value
                    summary_player = get_summary_model(players[(pos+1)%4])
                    summary_player.earned_coins
                    summary_player.save(update_fields=['earned_coins'])
                    create_game_transactions(
                        game=game, to_user=players[(pos+1)%4], amount=coins_value, status="cp",
                        descriptions=f"{player.alias} salio del juego {game.id}")
                    players[(pos+3)%4].earned_coins+=coins_value
                    create_game_transactions(
                        game=game, to_user=players[(pos+3)%4], amount=coins_value, status="cp",
                        descriptions=f"{player.alias} salio del juego {game.id}")
                    summary_player = get_summary_model(players[(pos+3)%4])
                    summary_player.earned_coins
                    summary_player.save(update_fields=['earned_coins'])
                    players[(pos+1)%4].save(update_fields=['earned_coins'])
                    players[(pos+3)%4].save(update_fields=['earned_coins'])     
                else:
                    n = len(players)-1
                    for p in players:
                        if p.alias != player.alias:
                            p.earned_coins+= int(coins/n)
                            create_game_transactions(
                                game=game, to_user=p, amount=int(coins/n), status="cp",
                                descriptions=f"{player.alias} salio del juego {game.id}")
                            summary_player = get_summary_model(p)
                            summary_player.earned_coins
                            summary_player.save(update_fields=['earned_coins'])
                            p.save(update_fields=['earned_coins'])
                player.earned_coins-=loss_coins
                if player.earned_coins<0:
                    player.recharged_coins += player.earned_coins
                    player.earned_coins = 0
                summary_player = get_summary_model(player)
                summary_player.loss_coins
                summary_player.save(update_fields=['loss_coins'])
                create_game_transactions(
                    game=game, from_user=player, amount=loss_coins, status="cp",
                    descriptions=f"por salir del juego {game.id}")
                bank.save(update_fields=['game_coins'])                               
            if totalPlayers <= 2 or game.inPairs:
                game.status = "wt"
                game.starter = -1
                game.board = ""
            elif (totalPlayers > 2 and not game.inPairs and game.perPoints) or game.status == "ru":
                game.status = "ready"
                game.starter = -1
            elif totalPlayers > 2 and not game.inPairs and game.status == "fg":
                if isStarter and game.startWinner:
                    game.starter = -1
                elif not isStarter:
                    if game.starter > pos:
                        game.starter-=1
                if game.winner < DominoGame.Tie_Game and game.winner > pos:
                    game.winner-=1
            player.isPlaying = False
        else:
            if totalPlayers <= 2 or game.inPairs:
                game.status = "wt"
                game.starter = -1
                game.board = ""
        reorderPlayers(game,player,players,starter)                                                       
        now = timezone.now()
        player.lastTimeInGame = now
        player.lastTimeInSystem = now
        player.save(update_fields=['points','tiles','isPlaying','earned_coins','recharged_coins','lastTimeInGame','lastTimeInSystem'])
        game.save(update_fields=['player1','player2','player3','player4','status','starter','winner','board'])    
    return exited    

def reorderPlayers(game:DominoGame, player:Player, players:list, starter:int):
    k = 0
    pos = getPlayerIndex(players,player)
    n = len(players)
    game.player1 = None
    game.player2 = None
    game.player3 = None
    game.player4 = None
    for i in range(n):
        if i != pos:
            if k == 0:
                game.player1 = players[i]
            elif k == 1:
                game.player2 = players[i]
            elif k == 2:
                game.player3 = players[i]
            elif k == 3:
                game.player4 = players[i]
            if starter == i:
                game.starter = k
            
            k+=1

#### Si todo sale bien se borra esta que es la vieja
def updateTeamScore_old(game: DominoGame, winner: int, players:list[Player], sum_points:int, move_register:MoveRegister, bank: Bank):
    n = len(players)
    if winner == DominoGame.Winner_Player_1 or winner == DominoGame.Winner_Player_3:
        game.scoreTeam1 += sum_points
        players[0].points+=sum_points
        players[2].points+=sum_points
        players[0].save(update_fields=['points'])
        players[2].save(update_fields=['points'])
    else:
        game.scoreTeam2 += sum_points
        players[1].points+=sum_points
        players[3].points+=sum_points
        players[1].save(update_fields=['points'])
        players[3].save(update_fields=['points'])
    if game.scoreTeam1 >= game.maxScore:
        game.status="fg"
        updatePlayersData(game,players,winner,"fg",move_register, bank)
        game.start_time = timezone.now()
        game.winner = DominoGame.Winner_Couple_1 #Gano el equipo 1
        if game.in_tournament:
            match = Match_Game.objects.get(game__id = game.id)
            match.games_win_team_1 += 1
            match.save(update_fields=["games_win_team_1"])
    elif game.scoreTeam2 >= game.maxScore:
        game.status="fg"
        updatePlayersData(game,players,winner,"fg", move_register, bank)
        game.start_time = timezone.now()
        game.winner = DominoGame.Winner_Couple_2 #Gano el equipo 2
        if game.in_tournament:
            match = Match_Game.objects.get(game__id = game.id)
            match.games_win_team_2 += 1
            match.save(update_fields=["games_win_team_2"])
    else:
        updatePlayersData(game,players,winner,"fi",move_register, bank)
        game.status="fi"    
###########################################################

def updateTeamScore(game: DominoGame, winner: int, players: list[Player], sum_points: int, move_register: MoveRegister, update_bank_coins: int):
    # 1. Determinar equipo ganador y jugadores a actualizar
    # Asumimos: Equipo 1 (índices 0, 2), Equipo 2 (índices 1, 3)
    is_team_1 = winner in [DominoGame.Winner_Player_1, DominoGame.Winner_Player_3]
    team_indices = [0, 2] if is_team_1 else [1, 3]
    
    # Actualizamos los objetos en memoria por si se usan después en esta misma función
    for i in team_indices:
        players[i].points += sum_points
        players[i].save(update_fields=['points'])

    # 3. Actualizar score del juego en memoria
    if is_team_1:
        game.scoreTeam1 += sum_points
    else:
        game.scoreTeam2 += sum_points

    # 4. Lógica de finalización de juego
    if game.scoreTeam1 >= game.maxScore or game.scoreTeam2 >= game.maxScore:
        game.status = "fg"
        game.start_time = timezone.now()
        game.winner = DominoGame.Winner_Couple_1 if game.scoreTeam1 >= game.maxScore else DominoGame.Winner_Couple_2
        
        # Optimización de Torneo: Update directo sin traer el objeto a memoria
        if game.in_tournament:
            field_to_inc = "games_win_team_1" if game.scoreTeam1 >= game.maxScore else "games_win_team_2"
            Match_Game.objects.filter(game__id=game.id).update(**{field_to_inc: F(field_to_inc) + 1})
            
        updatePlayersData(game, players, winner, "fg", move_register, update_bank_coins)
    else:
        game.status = "fi"
        updatePlayersData(game, players, winner, "fi", move_register, update_bank_coins)

    # Nota: Asegúrate de que el objeto 'game' se guarde después de llamar a esta función 
    # o añade game.save() aquí si es necesario.

##### si todo sale bien se borra este que es viejo
def updateAllPoints_old(game:DominoGame,players:list[Player],winner:int,move_register:MoveRegister, bank: Bank, isCapicua=False):
    sum_points = 0
    n = len(players)
    if game.sumAllPoints:
        for i in range(n):
            sum_points+=totalPoints(players[i].tiles)
        if isCapicua and game.capicua:
            sum_points*=2     
        if game.inPairs:
            updateTeamScore(game,winner,players,sum_points,move_register, bank)                
        else:
            players[winner].points+=sum_points
            players[winner].save(update_fields=['points'])
            if players[winner].points >= game.maxScore:
                game.status = "fg"
                updatePlayersData(game,players,winner,"fg",move_register, bank)
            else:
                game.status = "fi"
                updatePlayersData(game,players,winner,"fi",move_register, bank)                              
    else:#En caso en que se sumen los puntos solo de los perdedores
        for i in range(n):
            if i != winner:
                sum_points+=totalPoints(players[i].tiles)
        if game.inPairs:
            patner = (winner+2)%4
            sum_points-=totalPoints(players[patner].tiles)
            if isCapicua and game.capicua:
                sum_points*=2
            updateTeamScore(game,winner,players,sum_points,move_register)
        else:
            if isCapicua and game.capicua:
                sum_points*=2
            players[winner].points+=sum_points
            players[winner].save(update_fields=['points'])
            if players[winner].points >= game.maxScore:
                game.status = "fg"
                updatePlayersData(game,players,winner,"fg", move_register, bank)
            else:
                game.status = "fi"
                updatePlayersData(game,players,winner,"fi", move_register, bank)
###############################################################

def updateAllPoints(game: DominoGame, players: list[Player], winner: int, move_register: MoveRegister, update_bank_coins: int, isCapicua=False):
    # 1. Cálculo de puntos base usando comprensión de listas (más rápido)
    all_tiles_points = [totalPoints(p.tiles) for p in players]
    
    if game.sumAllPoints:
        sum_points = sum(all_tiles_points)
    else:
        # Sumar todos excepto el ganador
        sum_points = sum(all_tiles_points) - all_tiles_points[winner]
        # Si es por parejas, también restamos los puntos del compañero
        if game.inPairs:
            partner_idx = (winner + 2) % 4
            sum_points -= all_tiles_points[partner_idx]

    # 2. Aplicar multiplicador de Capicua una sola vez
    if isCapicua and game.capicua:
        sum_points *= 2

    # 3. Delegar o ejecutar la actualización
    if game.inPairs:
        # Reutilizamos la función optimizada anterior
        updateTeamScore(game, winner, players, sum_points, move_register, update_bank_coins)
    else:
        # Actualización atómica del jugador individual
        winner_player = players[winner]
        winner_player.points += sum_points
        winner_player.save(update_fields=['points'])
        
        # Determinar estado final
        is_final_game = winner_player.points >= game.maxScore
        game.status = "fg" if is_final_game else "fi"
        
        # Llamada única a updatePlayersData
        updatePlayersData(game, players, winner, game.status, move_register, update_bank_coins)

    # Nota: El objeto 'game' debe guardarse al final del proceso principal

def getPlayerIndex(players: list[Player],player: Player):
    for i in range(len(players)):
        if player.id == players[i].id:
            return i
    return -1

def updateSides(game:DominoGame,tile:str):
    values = tile.split('|')
    value1 = int(values[0])
    value2 = int(values[1])
    if len(game.board) == 0:
        game.leftValue = value1
        game.rightValue = value2
    else:    
        if value1 == game.leftValue:
            game.leftValue = value2
        else:
            game.rightValue = value2    

def updateTiles(player:Player,tile:str):
    tiles = player.tiles.split(',')

    inverse = rTile(tile)
    res = ''
    for s in tiles:
        if tile == s:
            tiles.remove(tile)
        elif inverse == s:
            tiles.remove(inverse)

    for i in range(len(tiles)):
        res+=tiles[i]
        if i < (len(tiles)-1):
            res+=','        
    return len(tiles),res

def getWinner(players,inPairs,variant):
    i = 0
    min = 1000
    res = -1
    points = []
    for player in players:
        pts = totalPoints(player.tiles)
        points.append(pts)
        if pts < min:
            min = pts
            res = i
        elif pts == min:
            res = 4
        i+=1
    if variant == "d6" and inPairs:
        sum1 = points[0]+points[2]
        sum2 = points[1]+points[3]
        if sum1 < sum2:
            if points[0] < points[2]:
                return DominoGame.Winner_Player_1
            else:
                return DominoGame.Winner_Player_3
        elif sum1 > sum2:
            if points[1] < points[3]:
                return DominoGame.Winner_Player_2
            else:
                return DominoGame.Winner_Player_4
        else:
            return DominoGame.Tie_Game        
    elif res == DominoGame.Tie_Game and inPairs:
        if points[0] == points[2] and points[2] == min and points[1] != min and points[3] != min:
            res = DominoGame.Winner_Player_1
        elif points[1] == points[3] and points[1] == min and points[0] != min and points[2] != min:
            res = DominoGame.Winner_Player_2         
    return res

def totalPoints(tiles):
    if len(tiles) == 0:
        return 0
    total = 0
    list_tiles = tiles.split(',')
    for tile in list_tiles:
        total+=getPoints(tile)
    return total

def getPoints(tile):
    values = tile.split('|')
    return int(values[0])+int(values[1])    

def checkClosedGame1(game:DominoGame, playersCount: int):
    tiles = game.board.split(',')
    lastPasses = 0
    rtiles = reversed(tiles)
    for tile in rtiles:
        if len(tile) > 0:
            if(isPass(tile)):
                lastPasses+=1
                if lastPasses == playersCount-1:
                    return True
            else:
                return False    
    return False
   
def isPass(tile):
    values = tile.split('|')
    return values[0] == "-1"

def playersCount(game: DominoGame)-> list[Player]:
    players = []
    if game.player1 is not None:
        players.append(game.player1)
    if game.player2 is not None:
        players.append(game.player2)
    if game.player3 is not None:
        players.append(game.player3)
    if game.player4 is not None:
        players.append(game.player4)
    return players

def shuffle(game:DominoGame, players:list[Player]):
    tiles = []
    max = 0
    if game.variant == "d6":
        max = 7
    else:
        max = 10

    for i in range(max):
        for j in range(i,max):
            tiles.append(str(j)+"|"+str(i))
    
    random.shuffle(tiles)

    for i in range(len(players)):
        player = players[i]
        player.tiles = ""
        if game.status !="fi":
            player.isPlaying = True
        if game.perPoints and (game.status =="ready" or game.status =="fg"):
            player.points = 0  
        for j in range(max):
            player.tiles+=tiles[i*max+j]
            if j < (max-1):
                player.tiles+=","
        player.save(update_fields=['tiles','isPlaying','points'])    
    
def checkCapicua(game,tile):
    if game.leftValue == game.rightValue:
        return False
    values = tile.split('|')
    val1 = int(values[0])
    val2 = int(values[1])
    return (val1 == game.leftValue and game.rightValue == val2) or (val2 == game.leftValue and game.rightValue == val1) 

def updateLastPlayerTime(game:DominoGame,alias:str):
    if game.player1 is not None and game.player1.alias == alias:
        game.lastTime1 = timezone.now()
    elif game.player2 is not None and game.player2.alias == alias:
        game.lastTime2 = timezone.now()
    if game.player3 is not None and game.player3.alias == alias:
        game.lastTime3 = timezone.now()
    if game.player4 is not None and game.player4.alias == alias:
        game.lastTime4 = timezone.now()
    game.save(update_fields=["lastTime1", "lastTime2", "lastTime3", "lastTime4"])

def takeRandomTile(tiles):
    list_tiles = tiles.split(',')
    
    max_double = None
    max_sum = -1
    max_tile = None
    
    for tile in list_tiles:
        num1, num2 = map(int, tile.split('|'))
        current_sum = num1 + num2
        
        # Buscar el mayor doble
        if num1 == num2:
            if current_sum > max_sum or max_double is None:
                max_double = tile
                max_sum = current_sum
                
        # Mientras tanto también buscamos la ficha con mayor suma
        if current_sum > max_sum or max_tile is None:
            max_tile = tile
            max_sum = current_sum
    
    # Devolver el mayor doble si existe, sino la mayor ficha
    return max_double if max_double is not None else max_tile

def takeRandomCorrectTile(tiles,left,right):
    list_tiles = tiles.split(',')
    best_tile = None
    best_sum = -1
    
    for tile in list_tiles:
        val1, val2 = map(int, tile.split('|'))
        current_sum = val1 + val2
        is_double = (val1 == val2)
        is_valid = (val1 == left or val1 == right or val2 == left or val2 == right)
        
        if is_valid:
            # Si es mejor que la actual (suma mayor o misma suma pero es doble)
            if (current_sum > best_sum) or (current_sum == best_sum and is_double):
                best_tile = tile if not is_double and (val1 == left or val1 == right) else rTile(tile)
                best_sum = current_sum
    
    return best_tile if best_tile is not None else "-1|-1"

def isMyTurn(board:str,myPos:int,starter:int,n:int, next_player:int):
    return myPos == next_player

def getLastMoveTime(game,player):
    if game.player1 is not None and game.player1.alias == player.alias:
        return game.lastTime1
    elif game.player2 is not None and game.player2.alias == player.alias:
        return game.lastTime2
    elif game.player3 is not None and game.player3.alias == player.alias:
        return game.lastTime3
    elif game.player4 is not None and game.player4.alias == player.alias:
        return game.lastTime4
    return None

def havepoints(game: DominoGame):
    """
    Retorna si algun jugador tiene puntos en una mesa por puntos
    """
    have_points = False
    if game.perPoints:
        if game.player1 is not None and not have_points:
            have_points = game.player1.points>0
        elif game.player2 is not None and not have_points:
            have_points = game.player2.points>0
        elif game.player3 is not None and not have_points:
            have_points = game.player3.points>0
        elif game.player4 is not None and  not have_points:
            have_points = game.player4.points>0
    return have_points

def ready_to_play(game: DominoGame, player: Player)->bool:
    '''
        Comprueba si el player tiene suficientes monedas para jugar en la mesa
    '''
    
    min_amount = 0
    
    pass_number = 5
    if game.variant == 'd6':
        pass_number = 3

    if game.perPoints and game.payMatchValue>0:
        min_amount = game.payMatchValue
    elif not game.perPoints and (game.payPassValue>0 or game.payWinValue>0):
        min_amount = game.payWinValue + (game.payPassValue * pass_number)
    
    if player.total_coins >= min_amount:
        return True
    
    return False   