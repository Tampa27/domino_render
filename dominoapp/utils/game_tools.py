from rest_framework.response import Response
from ..models import Player
from ..models import DominoGame, MoveRegister
from ..models import Bank
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
import random
from django.db import transaction
import logging
from dominoapp.utils.transactions import create_game_transactions
from dominoapp.connectors.pusher_connector import PushNotificationConnector
from dominoapp.utils.constants import ApiConstants
from dominoapp.utils.move_register_utils import movement_register

logger = logging.getLogger(__name__)


def setWinner1(game: DominoGame, winner: int):
    game.winner = winner
    game.start_time = timezone.now()


def setWinnerStarterNext1(game: DominoGame, winner: int, starter: int, next_player: int):
    game.starter = starter
    game.winner = winner
    game.next_player = next_player
    game.start_time = timezone.now()


def checkPlayerJoined(player,game):
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


def startGame1(game_id,players):
    with transaction.atomic():
        game = DominoGame.objects.select_for_update().get(id=game_id)
        # if game.status != "fi":
        #     for player in players:
        #         if player.isPlaying == False:
        #             player.isPlaying = True
        #             #player.save()
        # players_ru = []
        # for player in players:
        #     if player.isPlaying:
        #         players_ru.append(player)       
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
        #game.winner=-1

        try:
            bank = Bank.objects.all().first()
        except:
            bank = Bank.objects.create()
        
        ### Pensar aqui en que lugar sumo las datas y los game
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

        #if game.inPairs and (game.status =="ready" or game.status =="fg") and (game.payMatchValue > 0 or game.payWinValue > 0):
        #    shuffleCouples(game,players_ru)    
        shuffle(game,players)          
        game.status = "ru"
        game.start_time = timezone.now()
        game.leftValue = -1
        game.rightValue = -1
        game.lastTime1 = timezone.now()
        game.lastTime2 = timezone.now()
        game.lastTime3 = timezone.now()
        game.lastTime4 = timezone.now()
        game.save()


def movement(game_id,player,players,tile, automatic=False):
    with transaction.atomic():
        try:
            game = DominoGame.objects.select_for_update().get(id=game_id)
        except:
            return Response({'status': 'error', "message":"Game not found"}, status=404)
        n = len(players)
        w = getPlayerIndex(players,player)
        passTile = isPass(tile)
        
        if isMyTurn(game.board,w,game.starter,n) == False:
            logger.warning(player.alias+" intento mover "+tile +" pero se detecto que no es su turno")
            return(f"{player.alias} intento mover {tile} pero se detecto que no es su turno")
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
        
        if passTile == False:
            isCapicua = False
            if game.perPoints:
                isCapicua = checkCapicua(game,tile)
            
            move_register = movement_register(game, player, tile, players, automatic) 
            updateSides(game,tile)
            tiles_count,tiles = updateTiles(player,tile)
            player.tiles = tiles
            player.save()
            player.refresh_from_db()
            if tiles_count == 0:
                game.status = 'fg'
                game.start_time = timezone.now()
                if game.startWinner:
                    game.starter = w
                    game.next_player = w
                else:
                    game.starter = (game.starter+1)%n
                    game.next_player = game.starter    
                game.winner = w
                if game.perPoints:
                    game.rounds+=1
                    updateAllPoints(game,players,w,move_register,isCapicua)
                else:
                    updatePlayersData(game,players,w,"fg",move_register)
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
            if winner < DominoGame.Tie_Game:
                if game.startWinner:
                    game.starter = winner
                    game.next_player = winner
                else:
                    game.starter = (game.starter+1)%n
                    game.next_player = game.starter        
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
                updatePlayersData(game,players,winner,"fg",move_register)
                if game.inPairs and winner < DominoGame.Tie_Game:
                    if winner == DominoGame.Winner_Player_1 or winner == DominoGame.Winner_Player_3:
                        game.winner = DominoGame.Winner_Couple_1
                    elif winner == DominoGame.Winner_Player_2 or winner == DominoGame.Winner_Player_4:
                        game.winner = DominoGame.Winner_Couple_2                
        else:
            move_register = movement_register(game, player, tile, players, automatic) 
            if game.payPassValue > 0:
                updatePassCoins(w,game,players, move_register)
            game.next_player = (w+1) % n
        
        try:
            bank = Bank.objects.all().first()
        except:
            bank = Bank.objects.create()
       
        if game.status == "fg":
            bank.data_completed+=1
            bank.game_completed+=1
        elif game.status == "fi":
            bank.data_completed+=1
        
        bank.save(update_fields=["data_completed","game_completed"])

        game.board += (tile+',')
        game.save()
        game.refresh_from_db()
        logger.info(player.alias+" movio "+tile)
        PushNotificationConnector.push_notification(
                channel=f'mesa_{game.id}',
                event_name='move_tile',
                data_notification={
                    'game_status': game.status,
                    'player': player.id,
                    'tile': tile,
                    'next_player': game.next_player,
                    'time': timezone.now().strftime("%d/%m/%Y, %H:%M:%S")
                }
            )
        return None        

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

def updatePlayersData(game,players,w,status,move_register: MoveRegister):
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
            if i == w or i == ((w+2)%4):
                players[i].dataWins+=1
                if game.payWinValue > 0:
                    bank_coins = int(game.payWinValue*ApiConstants.DISCOUNT_PERCENT/100)
                    player_coins = (game.payWinValue-bank_coins)
                    bank.game_coins+=(bank_coins)
                    players[i].earned_coins+= player_coins
                    create_game_transactions(
                        game=game,to_user=players[i], amount=player_coins, status="cp", 
                        descriptions=f"gane en el juego {game.id}",
                        move_register=move_register)
                if status == "fg" and game.perPoints:
                    players[i].matchWins+=1
                    if game.payMatchValue > 0:
                        bank_coins = int(game.payMatchValue*ApiConstants.DISCOUNT_PERCENT/100)
                        bank.game_coins+=bank_coins
                        player_coins = (game.payMatchValue-bank_coins)
                        players[i].earned_coins+= player_coins
                        create_game_transactions(
                            game=game, to_user=players[i], amount=player_coins, status="cp", 
                            descriptions=f"gane en el juego {game.id}",
                            move_register=move_register)
                players[i].save()
            else:
                players[i].dataLoss+=1
                if game.payWinValue > 0 and w != 4:
                    players[i].earned_coins-=game.payWinValue
                    if players[i].earned_coins<0:
                        players[i].recharged_coins += players[i].earned_coins
                        players[i].earned_coins = 0
                    create_game_transactions(
                        game=game, from_user=players[i], amount=game.payWinValue, status="cp", 
                        descriptions=f"perdi en el juego {game.id}",
                        move_register=move_register)
                if status == "fg" and game.perPoints:
                    players[i].matchLoss+=1
                    if game.payMatchValue > 0 and w != 4:
                        players[i].earned_coins-=game.payMatchValue
                        if players[i].earned_coins<0:
                            players[i].recharged_coins += players[i].earned_coins
                            players[i].earned_coins = 0
                        create_game_transactions(
                            game=game, from_user=players[i], amount=game.payMatchValue, status="cp", 
                            descriptions=f"perdi en el juego {game.id}",
                            move_register=move_register)
                players[i].save()
    else:
        for i in range(n):
            if i == w:
                players[i].dataWins+=1
                if game.payWinValue > 0:
                    bank_coins = int(game.payWinValue*(n_p-1)*ApiConstants.DISCOUNT_PERCENT/100)
                    bank.game_coins+=bank_coins
                    player_coins = (game.payWinValue*(n_p-1)-bank_coins)
                    players[i].earned_coins+= player_coins
                    create_game_transactions(
                        game=game, to_user=players[i], amount=player_coins, status="cp", 
                        descriptions=f"gane en el juego {game.id}",
                        move_register=move_register)
                if status == "fg" and game.perPoints:
                    players[i].matchWins+=1
                    if game.payMatchValue > 0:
                        bank_coins = int(game.payMatchValue*(n_p-1)*ApiConstants.DISCOUNT_PERCENT/100)
                        bank.game_coins+=bank_coins
                        player_coins = (game.payMatchValue*(n_p-1)-bank_coins)
                        players[i].earned_coins+= player_coins
                        create_game_transactions(
                            game=game, to_user=players[i], amount=player_coins, status="cp", 
                            descriptions=f"gane en el juego {game.id}",
                            move_register=move_register)
                players[i].save()
            elif players[i].isPlaying == True:
                players[i].dataLoss+=1
                if game.payWinValue > 0 and w != 4:
                    players[i].earned_coins-=game.payWinValue
                    if players[i].earned_coins<0:
                            players[i].recharged_coins += players[i].earned_coins
                            players[i].earned_coins = 0
                    create_game_transactions(
                        game=game, from_user=players[i], amount=game.payWinValue, status="cp", 
                        descriptions=f"perdi en el juego {game.id}",
                        move_register=move_register)
                if status == "fg" and game.perPoints:
                    players[i].matchLoss+=1
                    if game.payMatchValue > 0 and w != 4:
                        players[i].earned_coins-=game.payMatchValue
                        if players[i].earned_coins<0:
                            players[i].recharged_coins += players[i].earned_coins
                            players[i].earned_coins = 0
                        create_game_transactions(
                            game=game, from_user=players[i], amount=game.payMatchValue, status="cp", 
                            descriptions=f"perdi en el juego {game.id}",
                            move_register=move_register)
                players[i].save()                                    
    bank.save(update_fields=['game_coins'])

def updatePassCoins(pos,game,players,move_register:MoveRegister):
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
                        players[pos].save()
                        players[pos1].save()
                    else:
                        pos1 = pos - prev
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
                        players[pos].save()
                        players[pos1].save()
                elif prev == 2 and game.inPairs == False:
                    if (pos - 2) < 0:
                        pos1 = pos + (n-prev)
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
                        players[pos].save()
                        players[pos1].save()
                    else:        
                        pos1 = pos - prev
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
                        players[pos].save()
                        players[pos1].save()
                break                            


def move1(game_id,alias,tile):
    # game = DominoGame.objects.select_for_update(nowait=True).get(id=game_id)
    game = DominoGame.objects.get(id=game_id)
    players = playersCount(game)
    players_ru = list(filter(lambda p: p.isPlaying,players))
    for p in players:
        if p.alias == alias:
            player = p
    # currentPlayer = Player.objects.select_for_update(nowait=False).get(id=player.id)      
    error = movement(game_id,player,players_ru,tile)
    
    updateLastPlayerTime(game,alias)
    if game.player1 and game.player1.id:
        game.player1.save() 
    if game.player2 and game.player2.id:
        game.player2.save() 
    if game.player3 and game.player3.id:
        game.player3.save()
    if game.player4 and game.player4.id:
        game.player4.save() 
    
    return error


def shuffleCouples(game,players):
    random.shuffle(players)
    game.player1 = players[0]
    game.player2 = players[1]
    game.player3 = players[2]
    game.player4 = players[3]

def exitPlayer(game: DominoGame, player: Player, players: list, totalPlayers: int):
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
                    create_game_transactions(
                        game=game, to_user=players[(pos+1)%4], amount=coins_value, status="cp",
                        descriptions=f"{player.alias} salio del juego {game.id}")
                    players[(pos+3)%4].earned_coins+=coins_value
                    create_game_transactions(
                        game=game, to_user=players[(pos+3)%4], amount=coins_value, status="cp",
                        descriptions=f"{player.alias} salio del juego {game.id}")
                    players[(pos+1)%4].save()
                    players[(pos+3)%4].save()     
                else:
                    n = len(players)-1
                    for p in players:
                        if p.alias != player.alias:
                            p.earned_coins+= int(coins/n)
                            create_game_transactions(
                                game=game, to_user=p, amount=int(coins/n), status="cp",
                                descriptions=f"{player.alias} salio del juego {game.id}")
                            p.save()
                player.earned_coins-=loss_coins
                if player.earned_coins<0:
                    player.recharged_coins += player.earned_coins
                    player.earned_coins = 0
                
                create_game_transactions(
                    game=game, from_user=player, amount=loss_coins, status="cp",
                    descriptions=f"por salir del juego {game.id}")
                bank.save(update_fields=['game_coins'])                               
            if totalPlayers <= 2 or game.inPairs:
                game.status = "wt"
                game.starter = -1
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
        reorderPlayers(game,player,players,starter)                                                       
        player.save()
        game.save()    
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

def updateTeamScore(game: DominoGame, winner: int, players, sum_points, move_register:MoveRegister):
    n = len(players)
    if winner == DominoGame.Winner_Player_1 or winner == DominoGame.Winner_Player_3:
        game.scoreTeam1 += sum_points
        players[0].points+=sum_points
        players[2].points+=sum_points
        players[0].save()
        players[2].save()
    else:
        game.scoreTeam2 += sum_points
        players[1].points+=sum_points
        players[3].points+=sum_points
        players[1].save()
        players[3].save()
    if game.scoreTeam1 >= game.maxScore:
        game.status="fg"
        updatePlayersData(game,players,winner,"fg",move_register)
        game.start_time = timezone.now()
        game.winner = DominoGame.Winner_Couple_1 #Gano el equipo 1
    elif game.scoreTeam2 >= game.maxScore:
        game.status="fg"
        updatePlayersData(game,players,winner,"fg", move_register)
        game.start_time = timezone.now()
        game.winner = DominoGame.Winner_Couple_2 #Gano el equipo 2
    else:
        updatePlayersData(game,players,winner,"fi",move_register)
        game.status="fi"    
    
def updateAllPoints(game,players,winner,move_register:MoveRegister,isCapicua=False):
    sum_points = 0
    n = len(players)
    if game.sumAllPoints:
        for i in range(n):
            sum_points+=totalPoints(players[i].tiles)
        if isCapicua and game.capicua:
            sum_points*=2     
        if game.inPairs:
            updateTeamScore(game,winner,players,sum_points,move_register)                
        else:
            players[winner].points+=sum_points
            players[winner].save()
            if players[winner].points >= game.maxScore:
                game.status = "fg"
                updatePlayersData(game,players,winner,"fg",move_register)
            else:
                game.status = "fi"
                updatePlayersData(game,players,winner,"fi",move_register)                              
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
            players[winner].save()
            if players[winner].points >= game.maxScore:
                game.status = "fg"
                updatePlayersData(game,players,winner,"fg", move_register)
            else:
                game.status = "fi"
                updatePlayersData(game,players,winner,"fi", move_register)    

def getPlayerIndex(players,player):
    for i in range(len(players)):
        if player.id == players[i].id:
            return i
    return -1

def updateSides(game,tile):
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

def updateTiles(player,tile):
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

def checkClosedGame1(game, playersCount):
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

def playersCount(game):
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

def shuffle(game, players):
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
        player.save()    

def checkCapicua(game,tile):
    if game.leftValue == game.rightValue:
        return False
    values = tile.split('|')
    val1 = int(values[0])
    val2 = int(values[1])
    return (val1 == game.leftValue and game.rightValue == val2) or (val2 == game.leftValue and game.rightValue == val1) 

def updateLastPlayerTime(game,alias):
    game.refresh_from_db()
    if game.player1 is not None and game.player1.alias == alias:
        game.lastTime1 = timezone.now()
    elif game.player2 is not None and game.player2.alias == alias:
        game.lastTime2 = timezone.now()
    if game.player3 is not None and game.player3.alias == alias:
        game.lastTime3 = timezone.now()
    if game.player4 is not None and game.player4.alias == alias:
        game.lastTime4 = timezone.now()
    game.save()

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

def isMyTurn(board,myPos,starter,n):
    moves_count = len(board.split(","))-1
    res = moves_count%n
    return (starter+res)%n == myPos

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