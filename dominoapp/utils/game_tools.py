from rest_framework.response import Response
from ..models import Player
from ..models import DominoGame, MoveRegister, DataGame, MatchGame
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


def setWinner1(data_game: DataGame,winner: int):
    data_game.winner = winner
    data_game.start_time = timezone.now()


def setWinnerStarterNext1(data_game: DataGame,winner:int,starter:int,next_player:int):
    data_game.starter = starter
    data_game.winner = winner
    data_game.next_player = next_player
    data_game.start_time = timezone.now()


def checkPlayerJoined(player:Player, data_game:DataGame):
    res = False
    players = []
    if data_game.player1 is not None:
        players.append(data_game.player1)
        if data_game.player1.alias == player.alias:
            res = True
    if data_game.player2 is not None:
        players.append(data_game.player2)
        if data_game.player2.alias == player.alias:
            res = True
    if data_game.player3 is not None:
        players.append(data_game.player3)
        if data_game.player3.alias == player.alias:
            res = True
    if data_game.player4 is not None:
        players.append(data_game.player4)
        if data_game.player4.alias == player.alias:
            res = True
    return res,players

def joinplayer(data_game:DataGame, player:Player, players:list[Player]):
    joined = False
    
    if data_game.player1 is None:
        data_game.player1 = player
        joined = True
        players.insert(0,player)
    elif data_game.player2 is None:
        data_game.player2 = player
        joined = True
        players.insert(1,player)
    elif data_game.player3 is None:
        data_game.player3 = player
        joined = True
        players.insert(2,player)
    elif data_game.player4 is None:
        data_game.player4 = player
        joined = True
        players.insert(3,player)
    return joined,players


def startGame1(game_id:int,players:list[Player]):
    with transaction.atomic():
        game = DominoGame.objects.select_for_update().get(id=game_id)
        data_game = DataGame.objects.filter(active=True, match__domino_game__id = game.id).order_by('-id').first()
        
        n = len(players)
        if data_game.status == 'fi':
            match = data_game.match
            if data_game.match.status == 'fg':
                match = MatchGame.objects.create(
                    domino_game = game,
                    rounds = 0,
                    active = True,
                    status = 'ru'
                )
                data_game.match.active = False
                data_game.match.save(update_fields=['active'])

            new_data_game = DataGame.objects.create(
                match = match,
                active = True,
                status = 'ru',
                starter = data_game.starter,
                next_player = data_game.next_player                         
                )
            
            data_game.active = False
            data_game.save(update_fields=['active'])
            
            data_game = new_data_game
            k = 0
            for i in range(n):
                if k == 0:
                    data_game.player1 = players[i]
                elif k == 1:
                    data_game.player2 = players[i]
                elif k == 2:
                    data_game.player3 = players[i]
                elif k == 3:
                    data_game.player4 = players[i]
                k+=1
            
            data_game.save()
                
        
        # if game.status != "fi":
        #     for player in players:
        #         if player.isPlaying == False:
        #             player.isPlaying = True
        #             #player.save()
        # players_ru = []
        # for player in players:
        #     if player.isPlaying:
        #         players_ru.append(player)       
        
        if data_game.starter == -1 or data_game.starter >= n:
            data_game.next_player = random.randint(0,n-1)
            data_game.starter = data_game.next_player
        # else:
            # if players[game.starter].alias != players_ru[game.starter].alias:
            #     game.starter = getPlayerIndex(players_ru,players[game.starter])

        if game.inPairs and data_game.winner != 4:
            if data_game.starter == 0 or data_game.starter == 2:
                data_game.winner = 5
            else:
                data_game.winner = 6
        #game.winner=-1

        try:
            bank = Bank.objects.all().first()
        except:
            bank = Bank.objects.create()
        
        ### Pensar aqui en que lugar sumo las datas y los game
        bank.data_played+=1

        # new.board = ''
        if game.perPoints and (game.status =="ready" or game.status =="fg"):
        #     # old_data_game.match.scoreTeam1 = 0
        #     # old_data_game.match.scoreTeam2 = 0
        #     for player in players:
        #         player.points = 0
            # old_data_game.match.rounds = 0
            # old_data_game.match.save(update_fields=["rounds","scoreTeam1","scoreTeam2"])

            bank.game_played+=1
        elif not game.perPoints:
            bank.game_played+=1
        
        bank.save(update_fields=['game_played', 'data_played'])

        #if game.inPairs and (game.status =="ready" or game.status =="fg") and (game.payMatchValue > 0 or game.payWinValue > 0):
        #    shuffleCouples(game,players_ru)    
        shuffle(data_game,players)          
        data_game.status = "ru"
        data_game.match.status = "ru"
        data_game.match.rounds += 1
        data_game.start_time = timezone.now()
        data_game.lastTime1 = timezone.now()
        data_game.lastTime2 = timezone.now()
        data_game.lastTime3 = timezone.now()
        data_game.lastTime4 = timezone.now()
        data_game.match.save()
        data_game.save()


def movement(game_id:int,player: Player,players:list[Player],tile:str, automatic=False):
    with transaction.atomic():
        try:
            game = DominoGame.objects.select_for_update().get(id=game_id)
        except:
            return Response({'status': 'error', "message":"Game not found"}, status=404)
        n = len(players)
        w = getPlayerIndex(players,player)
        passTile = isPass(tile)
        
        data_game = DataGame.objects.select_for_update().get(match__domino_game__id = game.id, active=True)
        
        if isMyTurn(data_game.board,w,data_game.starter,n) == False:
            logger.warning(player.alias+" intento mover "+tile +" pero se detecto que no es su turno")
            return(f"{player.alias} intento mover {tile} pero se detecto que no es su turno")
        if noCorrect(data_game,tile):
            logger.warning(player.alias+" intento mover "+tile +" pero se detecto que no es una ficha correcta")
            return(f"{player.alias} intento mover {tile} pero se detecto que no es una ficha correcta")
        if (passTile and (game.status == 'fi' or game.status == 'fg')):
            logger.warning(player.alias+" intento mover "+tile +" pero se detecto que el juego habia terminado")
            return(f"{player.alias} intento mover {tile} pero se detecto que el juego habia terminado")
        if (len(data_game.board) == 0 and passTile):
            logger.warning(player.alias+" intento mover "+tile +" pero se detecto que el juego habia empezado")
            return(f"{player.alias} intento mover {tile} pero se detecto que el juego habia empezado")
        if CheckPlayerTile(tile, player) == False:
            logger.warning(player.alias+" intento mover "+tile +" pero se detecto que la ficha no le pertenese")
            return(f"{player.alias} intento mover {tile} pero se detecto que la ficha no le pertenese")
        if not CorrectPassTile(data_game,player,tile):
            logger.warning(player.alias+" intento mover "+tile +" pero se detecto que tenia fichas para jugar")
            return(f"{player.alias} intento pasarse con fichas")
        
        if passTile == False:
            isCapicua = False
            if game.perPoints:
                isCapicua = checkCapicua(data_game,tile)

            move_register = movement_register(data_game, player, tile, players, automatic) 
            updateSides(data_game,tile)
            tiles_count,tiles = updateTiles(player,tile)
            player.tiles = tiles
            player.save()
            player.refresh_from_db()
            if tiles_count == 0:
                # game.status = 'fg'
                data_game.status = 'fi'
                data_game.end_time = timezone.now()
                # game.start_time = timezone.now()
                if game.startWinner:
                    data_game.starter = w
                    data_game.next_player = w
                else:
                    data_game.starter = (data_game.starter+1)%n
                    data_game.next_player = data_game.starter    
                data_game.winner = w
                if game.perPoints:
                    updateAllPoints(game,data_game,players,w,move_register,isCapicua)
                else:
                    data_game.match.status = 'fg'
                    data_game.match.end_time = timezone.now()
                    updatePlayersData(game,players,w,"fg",move_register)                                        
            else:
                data_game.next_player = (w+1) % n 
        elif checkClosedGame1(data_game,n):
            move_register = movement_register(data_game, player, tile, players, automatic)
            winner = getWinner(players,game.inPairs,game.variant)
            # game.status = 'fg'
            data_game.status = 'fi'
            data_game.end_time = timezone.now()
            # game.start_time = timezone.now()
            data_game.winner = winner
            # if game.perPoints:
            #     ## Buscar otro lugar para saber si el juego termino o sigue
            #     data_game.match.rounds+=1
            if winner < 4:
                if game.startWinner:
                    data_game.starter = winner
                    data_game.next_player = winner
                else:
                    data_game.starter = (data_game.starter+1)%n
                    data_game.next_player = data_game.starter        
            if game.perPoints and winner < 4:
                updateAllPoints(game,data_game,players,winner,move_register)
            elif game.perPoints and winner == 4:
                # game.status = "fi"
                if game.startWinner and (game.lostStartInTie != True or game.inPairs == False):
                    data_game.next_player = data_game.starter
                else:    
                    data_game.starter = (data_game.starter+1)%n
                    data_game.next_player = data_game.starter
            else:
                data_game.match.status = 'fg'
                data_game.match.end_time = timezone.now()
                updatePlayersData(game,players,winner,"fg",move_register)                
        else:
            move_register = movement_register(data_game, player, tile, players, automatic) 
            if game.payPassValue > 0:
                updatePassCoins(w,game,data_game,players, move_register)
            data_game.next_player = (w+1) % n

        data_game.board += (tile+',')
        data_game.save()
        data_game.match.save()
        game.save()
        game.refresh_from_db()
        
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

        logger.info(player.alias+" movio "+tile)
        PushNotificationConnector.push_notification(
                channel=f'mesa_{game.id}',
                event_name='move_tile',
                data_notification={
                    'game_status': game.status,
                    'player': player.id,
                    'tile': tile,
                    'next_player': data_game.next_player,
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

def CorrectPassTile(data_game: DataGame, player:Player, tile:str):
    tiles = player.tiles.split(',')
    if isPass(tile):        
        numbers = [int(side) for single in tiles for side in single.split('|')]
        if data_game.leftValue in numbers or data_game.rightValue in numbers:
            # Comprobar que realmente no lleva fichas
            return False
    return True 

def noCorrect(data_game: DataGame,tile:str):
    values = tile.split('|')
    val0 = int(values[0])
    if val0 == -1 or (data_game.leftValue == -1 and data_game.rightValue == -1):
        return False
    if data_game.leftValue == val0 or data_game.rightValue == val0:
        return False
    return True

def rTile(tile)->str:
    values = tile.split('|')
    return (values[1]+"|"+values[0])

def updatePlayersData(game:DominoGame,players:list[Player],w:int,status:str,move_register: MoveRegister):
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

def updatePassCoins(pos:int,game:DominoGame, data_game: DataGame,players:list[Player],move_register:MoveRegister):
    tiles = data_game.board.split(',')
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
                            descriptions=f"{players[pos1].alias} me paso en el juego {game.id}, a {data_game.leftValue} y a {data_game.rightValue}",
                            move_register=move_register)
                        create_game_transactions(
                            game=game, to_user=players[pos1], amount=coins, status="cp", 
                            descriptions=f"pase a {players[pos].alias} en el juego {game.id}, a {data_game.leftValue} y a {data_game.rightValue}",
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
                            descriptions=f"{players[pos1].alias} me paso en el juego {game.id}, a {data_game.leftValue} y a {data_game.rightValue}",
                            move_register=move_register)
                        create_game_transactions(
                            game=game, to_user=players[pos1], amount=coins, status="cp",
                            descriptions=f"pase a {players[pos].alias} en el juego {game.id}, a {data_game.leftValue} y a {data_game.rightValue}",
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
                            descriptions=f"{players[pos1].alias} me paso en el juego {game.id}, a {data_game.leftValue} y a {data_game.rightValue}",
                            move_register=move_register)
                        create_game_transactions(
                            game=game, to_user=players[pos1], amount=coins, status="cp",
                            descriptions=f"pase a {players[pos].alias} en el juego {game.id}, a {data_game.leftValue} y a {data_game.rightValue}",
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
                            descriptions=f"{players[pos1].alias} me paso en el juego {game.id}, a {data_game.leftValue} y a {data_game.rightValue}",
                            move_register=move_register)
                        create_game_transactions(
                            game=game, to_user=players[pos1], amount=coins, status="cp",
                            descriptions=f"pase a {players[pos].alias} en el juego {game.id}, a {data_game.leftValue} y a {data_game.rightValue}",
                            move_register=move_register)
                        players[pos].save()
                        players[pos1].save()
                break                            


def move1(game_id:int,alias:str,tile:str):
    # game = DominoGame.objects.select_for_update(nowait=True).get(id=game_id)
    game = DominoGame.objects.get(id=game_id)
    data_game = DataGame.objects.filter(match__domino_game__id = game.id, active=True).order_by('-id').first()
    players = playersCount(data_game)
    players_ru = list(filter(lambda p: p.isPlaying,players))
    for p in players:
        if p.alias == alias:
            player = p
    # currentPlayer = Player.objects.select_for_update(nowait=False).get(id=player.id)      
    error = movement(game_id,player,players_ru,tile)
    
    
    updateLastPlayerTime(data_game,alias)
    if data_game.player1 and data_game.player1.id==player.id:
        data_game.player1.save() 
    if data_game.player2 and data_game.player2.id==player.id:
        data_game.player2.save() 
    if data_game.player3 and data_game.player3.id==player.id:
        data_game.player3.save()
    if data_game.player4 and data_game.player4.id==player.id:
        data_game.player4.save() 
    
    return error


def shuffleCouples(data_game:DataGame,players:list[Player]):
    random.shuffle(players)
    data_game.player1 = players[0]
    data_game.player2 = players[1]
    data_game.player3 = players[2]
    data_game.player4 = players[3]

def exitPlayer(data_game: DataGame, player: Player, players: list[Player], totalPlayers: int):
    game = data_game.match.domino_game
    exited = False
    pos = getPlayerIndex(players,player)
    starter = data_game.starter
    isStarter = starter == pos
    lastTimeMove = getLastMoveTime(data_game,player)
    noActivity = False
    if lastTimeMove is not None:
        timediff = timezone.now() - lastTimeMove
        if timediff.seconds >= 60:
            noActivity = True
        
    if data_game.player1 is not None and data_game.player1.alias == player.alias:
        # data_game.player1 = None
        exited = True
    elif data_game.player2 is not None and data_game.player2.alias == player.alias:
        # data_game.player2 = None
        exited = True        
    elif data_game.player3 is not None and data_game.player3.alias == player.alias:
        # data_game.player3 = None
        exited = True
    elif data_game.player4 is not None and data_game.player4.alias == player.alias:
        # data_game.player4 = None
        exited = True
    
    if exited:
        # player.points = 0
        player.tiles = ""
        if player.isPlaying:
            have_points = havepoints(data_game.match)
            if (game.status == "fi" or (game.status == "ru" and (have_points or (data_game.board != "")))) and (game.payWinValue > 0 or game.payMatchValue > 0) and noActivity == False:
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
                # game.status = "wt"
                if data_game.status in ['wt', 'ready']:
                    data_game.status = "wt"
                    data_game.match.status = "wt"
                else:
                    data_game.status = "fi"
                    data_game.end_time = timezone.now()
                    data_game.match.status = "fg"
                    data_game.match.end_time = timezone.now()
            elif (totalPlayers > 2 and not game.inPairs and game.perPoints) or game.status == "ru":
                # game.status = "ready"
                if data_game.status in ['wt', 'ready']:
                    data_game.status = "ready"
                    data_game.match.status = "ready"
                else:
                    data_game.status = "fi"
                    data_game.end_time = timezone.now()
                    data_game.match.status = "fg"
                    data_game.match.end_time = timezone.now()
            elif totalPlayers > 2 and not game.inPairs and game.status == "fg":
                # if isStarter and game.startWinner:
                #     data_game.starter = -1
                # elif not isStarter:
                #     if data_game.starter > pos:
                #         data_game.starter-=1
                # if data_game.winner < 4 and data_game.winner > pos:
                #     data_game.winner-=1
                if data_game.active:
                    data_game.status = "fi"
                    # data_game.starter = -1
                    data_game.end_time = timezone.now()
                    data_game.match.status = "fg"
                    data_game.match.end_time = timezone.now()
            player.isPlaying = False
        else:
            if totalPlayers <= 2 or game.inPairs:
                # game.status = "wt"
                if data_game.status in ['wt', 'ready']:
                    data_game.status = "wt"
                    data_game.match.status = "wt"
                    
                else:
                    data_game.status = "fi"
                    data_game.end_time = timezone.now()
                    # data_game.starter = -1
                    data_game.match.status = "fg"
                    data_game.match.end_time = timezone.now()
                    
                    
        if data_game.status != "wt" and data_game.status != "ready":
            data_game.end_time = timezone.now()
            data_game.match.end_time = timezone.now()
        player.save()
        data_game.match.save()
        data_game.save()   
        reorderPlayers(game,data_game,player,players,starter)                                                       
              
    return exited    

def reorderPlayers(game: DominoGame,data_game:DataGame, player:Player, players:list, starter:int):
    k = 0
    pos = getPlayerIndex(players,player)
    n = len(players)
    if data_game.status in ['wt', 'ready']:
        data_game.player1 = None
        data_game.player2 = None
        data_game.player3 = None
        data_game.player4 = None
    else:
        data_game.active = False
        data_game.match.active = False
        data_game.save(update_fields=["active"])
        data_game.match.save(update_fields=["active"])
        macth = MatchGame.objects.create(
                                domino_game=game,
                                status="wt",
                                rounds=0,
                                active = True
                                )
        data_game = DataGame.objects.create(
                                match = macth,
                                status="wt",
                                active = True
                                )
    for i in range(n):
        if i != pos:
            if k == 0:
                data_game.player1 = players[i]
            elif k == 1:
                data_game.player2 = players[i]
                if not game.inPairs:
                    data_game.status = "ready"
                    data_game.match.status = "ready"
            elif k == 2:
                data_game.player3 = players[i]
            elif k == 3:
                data_game.player4 = players[i]
                if game.inPairs:
                    data_game.status = "ready"
                    data_game.match.status = "ready"
            if starter == i:
                data_game.starter = k
            k+=1
    data_game.save()
    data_game.match.save()

def updateTeamScore(game:DominoGame, data_game:DataGame, winner:int, players:list[Player], sum_points:int, move_register:MoveRegister):
    n = len(players)
    if winner == 0 or winner == 2:
        data_game.match.scoreTeam1 += sum_points
        data_game.match.score_player1 += sum_points
        data_game.match.score_player3 += sum_points
        data_game.score_player1 += sum_points
        data_game.score_player3 += sum_points
        # players[0].points+=sum_points
        # players[2].points+=sum_points
        # players[0].save()
        # players[2].save()
    else:
        data_game.match.scoreTeam2 += sum_points
        data_game.match.score_player2 += sum_points
        data_game.match.score_player4 += sum_points
        data_game.score_player2 += sum_points
        data_game.score_player4 += sum_points
        # players[1].points+=sum_points
        # players[3].points+=sum_points
        # players[1].save()
        # players[3].save()
    if data_game.match.scoreTeam1 >= game.maxScore:
        # game.status="fg"
        data_game.match.status = "fg"
        data_game.match.end_time = timezone.now()
        data_game.status = "fi"
        data_game.end_time = timezone.now()
        updatePlayersData(game,players,winner,"fg",move_register)
        # game.start_time = timezone.now()
        data_game.winner = 5 #Gano el equipo 1
    elif data_game.match.scoreTeam2 >= game.maxScore:
        # game.status="fg"
        data_game.match.status = "fg"
        data_game.match.end_time = timezone.now()
        data_game.status = "fi"
        data_game.end_time = timezone.now()
        updatePlayersData(game,players,winner,"fg", move_register)
        # game.start_time = timezone.now()
        data_game.winner = 6 #Gano el equipo 2
    else:
        updatePlayersData(game,players,winner,"fi",move_register)
        # game.status="fi"
        data_game.status = "fi"
        data_game.end_time = timezone.now()    
    
def updateAllPoints(game:DominoGame, data_game:DataGame, players:list[Player], winner:int, move_register:MoveRegister,isCapicua=False):
    sum_points = 0
    n = len(players)
    if game.sumAllPoints:
        for i in range(n):
            sum_points+=totalPoints(players[i].tiles)
        if isCapicua and game.capicua:
            sum_points*=2     
        if game.inPairs:
            updateTeamScore(game,data_game,winner,players,sum_points,move_register)                
        else:
            # players[winner].points+=sum_points
            # players[winner].save()
            setwinnerpoints(data_game,players,winner,sum_points)
            winner_points = getwinnerpoints(data_game,players,winner)
            if winner_points >= game.maxScore:
                # game.status = "fg"
                data_game.match.status = "fg"
                data_game.match.end_time = timezone.now()
                data_game.status = "fi"
                data_game.end_time = timezone.now()
                updatePlayersData(game,players,winner,"fg",move_register)
            else:
                # game.status = "fi"
                data_game.status = "fi"
                data_game.end_time = timezone.now()
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
            # players[winner].points+=sum_points
            # players[winner].save()
            setwinnerpoints(data_game,players,winner,sum_points)
            winner_points = getwinnerpoints(data_game,players,winner)
            if winner_points >= game.maxScore:
                # game.status = "fg"
                data_game.match.status = "fg"
                data_game.match.end_time = timezone.now()
                data_game.status = "fi"
                data_game.end_time = timezone.now()
                updatePlayersData(game,players,winner,"fg", move_register)
            else:
                # game.status = "fi"
                data_game.status = "fi"
                data_game.end_time = timezone.now()
                updatePlayersData(game,players,winner,"fi", move_register)    

def setwinnerpoints(data_game:DataGame, players:list[Player], winner:int, points:int):
    if data_game.player1 is not None and data_game.player1.id == players[winner].id:
        data_game.match.score_player1 += points
        data_game.score_player1 += points
    elif data_game.player2 is not None and data_game.player2.id == players[winner].id:
        data_game.match.score_player2 += points
        data_game.score_player2 += points
    elif data_game.player3 is not None and data_game.player3.id == players[winner].id:
        data_game.match.score_player3 += points
        data_game.score_player3 += points
    elif data_game.player4 is not None and data_game.player4.id == players[winner].id:
        data_game.match.score_player4 += points
        data_game.score_player4 += points
    data_game.match.save(update_fields=["score_player1","score_player2","score_player3","score_player4"])
    data_game.save(update_fields=["score_player1","score_player2","score_player3","score_player4"])

def getwinnerpoints(data_game:DataGame, players:list[Player], winner:int)->int:
    if data_game.player1 is not None and data_game.player1.id == players[winner].id:
        return data_game.match.score_player1
    elif data_game.player2 is not None and data_game.player2.id == players[winner].id:
        return data_game.match.score_player2
    elif data_game.player3 is not None and data_game.player3.id == players[winner].id:
        return data_game.match.score_player3
    elif data_game.player4 is not None and data_game.player4.id == players[winner].id:
        return data_game.match.score_player4
    return 0

def getplayerpoints(data_game:DataGame, player:Player)->int:
    if data_game.player1 is not None and data_game.player1.id == player.id:
        return data_game.match.score_player1
    elif data_game.player2 is not None and data_game.player2.id == player.id:
        return data_game.match.score_player2
    elif data_game.player3 is not None and data_game.player3.id == player.id:
        return data_game.match.score_player3
    elif data_game.player4 is not None and data_game.player4.id == player.id:
        return data_game.match.score_player4
    return 0

def getPlayerIndex(players: list[Player],player: Player):
    for i in range(len(players)):
        if player.id == players[i].id:
            return i
    return -1

def updateSides(data_game:DataGame,tile:str):
    values = tile.split('|')
    value1 = int(values[0])
    value2 = int(values[1])
    if len(data_game.board) == 0:
        data_game.leftValue = value1
        data_game.rightValue = value2
    else:    
        if value1 == data_game.leftValue:
            data_game.leftValue = value2
        else:
            data_game.rightValue = value2    

def updateTiles(player: Player,tile:str):
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

def getWinner(players:list[Player],inPairs:bool,variant:str):
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
                return 0
            else:
                return 2
        elif sum1 > sum2:
            if points[1] < points[3]:
                return 1
            else:
                return 3
        else:
            return 4        
    elif res == 4 and inPairs:
        if points[0] == points[2] and points[2] == min and points[1] != min and points[3] != min:
            res = 0
        elif points[1] == points[3] and points[1] == min and points[0] != min and points[2] != min:
            res = 1         
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

def checkClosedGame1(data_game: DataGame, playersCount:int):
    tiles = data_game.board.split(',')
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
   
def isPass(tile:str):
    values = tile.split('|')
    return values[0] == "-1"

def playersCount(data_game: DataGame):
    players = []
    if data_game.active:
        if data_game.player1 is not None:
            players.append(data_game.player1)
        if data_game.player2 is not None:
            players.append(data_game.player2)
        if data_game.player3 is not None:
            players.append(data_game.player3)
        if data_game.player4 is not None:
            players.append(data_game.player4)
    return players

def shuffle(data_game: DataGame, players):
    tiles = []
    max = 0
    if data_game.match.domino_game.variant == "d6":
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
        if data_game.status !="fi":
            player.isPlaying = True
        # if data_game.match.domino_game.perPoints and (data_game.match.domino_game.status =="ready" or data_game.match.domino_game.status =="fg"):
        #     player.points = 0  
        for j in range(max):
            player.tiles+=tiles[i*max+j]
            if j < (max-1):
                player.tiles+=","
        player.save()    

def checkCapicua(data_game: DataGame,tile:str):
    if data_game.leftValue == data_game.rightValue:
        return False
    values = tile.split('|')
    val1 = int(values[0])
    val2 = int(values[1])
    return (val1 == data_game.leftValue and data_game.rightValue == val2) or (val2 == data_game.leftValue and data_game.rightValue == val1) 

def updateLastPlayerTime(data_game:DataGame, alias:str):
    data_game.refresh_from_db()
    if data_game.player1 is not None and data_game.player1.alias == alias:
        data_game.lastTime1 = timezone.now()
    elif data_game.player2 is not None and data_game.player2.alias == alias:
        data_game.lastTime2 = timezone.now()
    if data_game.player3 is not None and data_game.player3.alias == alias:
        data_game.lastTime3 = timezone.now()
    if data_game.player4 is not None and data_game.player4.alias == alias:
        data_game.lastTime4 = timezone.now()
    data_game.save()

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

def takeRandomCorrectTile(tiles:str,left:int,right:int)->str:
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

def getLastMoveTime(data_game:DataGame, player:Player):
    if data_game.player1 is not None and data_game.player1.alias == player.alias:
        return data_game.lastTime1
    elif data_game.player2 is not None and data_game.player2.alias == player.alias:
        return data_game.lastTime2
    elif data_game.player3 is not None and data_game.player3.alias == player.alias:
        return data_game.lastTime3
    elif data_game.player4 is not None and data_game.player4.alias == player.alias:
        return data_game.lastTime4
    return None


def havepoints(match_game: MatchGame) -> bool:
    """
    Retorna si algun jugador tiene puntos en una mesa por puntos
    """
    if match_game.domino_game.perPoints:
        return any(
            [
                match_game.score_player1 > 0,
                match_game.score_player2 > 0,
                match_game.score_player3 > 0,
                match_game.score_player4 > 0,
                match_game.scoreTeam1 > 0,
                match_game.scoreTeam2 > 0
            ]  
        )

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