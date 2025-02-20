from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status 
from .models import Player
from .serializers import PlayerSerializer
from .serializers import MyPlayerSerializer
from .models import DominoGame
from .models import Bank
from .serializers import GameSerializer
from .serializers import BankSerializer
from django.shortcuts import get_object_or_404 
from rest_framework.decorators import api_view
from rest_framework import generics
from django.utils import timezone
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist
import random
from django.conf import settings
from django.views import View
from django.db import transaction
import asyncio
import threading
import time

# Create your views here.
class PlayerView(APIView):

    def get(self, request, id):
        result = Player.objects.get(id=id)
        if id:
            serializer = PlayerSerializer(result)
            return Response({"status":'success',"player":serializer.data},status=200)
        
        result = Player.objects.all()
        serializer = PlayerSerializer(result,many=True)
        return Response({"status":'success',"player":serializer.data},status=200)
    
    def post(self, request):  
        serializer = PlayerSerializer(data=request.data)  
        if serializer.is_valid():  
            serializer.save()  
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)  
        else:  
            return Response({"status": "error", "data": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
    def patch(self, request, id):  
        result = Player.objects.get(id=id)  
        serializer = PlayerSerializer(result, data = request.data, partial=True)  
        if serializer.is_valid():  
            serializer.save()  
            return Response({"status": "success", "data": serializer.data})  
        else:  
            return Response({"status": "error", "data": serializer.errors})  
  
    def delete(self, request, id=None):  
        result = get_object_or_404(Player, id=id)  
        result.delete()  
        return Response({"status": "success", "data": "Record Deleted"})    

class PlayerCreate(generics.CreateAPIView):
    queryset = Player.objects.all()
    serializer_class = MyPlayerSerializer
    def post(self, request, *args, **kwargs):    
        serializer = self.get_serializer(data=request.data)  
        if serializer.is_valid():  
            self.perform_create(serializer)  
            return Response({"status": "success", "player": serializer.data}, status=status.HTTP_200_OK)  
        else:  
            return Response({"status": "error", "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class PlayerUpdate(generics.CreateAPIView):
    queryset = Player.objects.all()
    serializer_class = MyPlayerSerializer        
    def patch(self, request, alias):  
        result = Player.objects.get(alias=alias)  
        serializer = self.get_serializer(result, data = request.data, partial=True)  
        if serializer.is_valid():  
            serializer.save()  
            return Response({"status": "success", "player": serializer.data})  
        else:  
            return Response({"status": "error", "data": serializer.errors})      

class PlayersView(APIView):
    def get(self, request, *args, **kwargs):  
        result = Player.objects.all()  
        serializers = PlayerSerializer(result, many=True)  
        return Response({'status': 'success', "players":serializers.data}, status=200)  

class GameCreate(generics.CreateAPIView):
    queryset = DominoGame.objects.all()
    serializer_class = GameSerializer
    def post(self, request, alias):    
        serializer = self.get_serializer(data=request.data)  
        if serializer.is_valid():  
            self.perform_create(serializer)  
            try:
                player1 = Player.objects.get(alias=alias)
            except ObjectDoesNotExist:
                return Response ({'status': 'error'},status=400)
            player1.tiles = ""
            player1.points=0
            player1.lastTimeInSystem = timezone.now()
            player1.save()
            players = [player1]
            data = serializer.validated_data
            data['player1']=player1
            serializer.save(player1=data['player1'])
            playerSerializer = PlayerSerializer(players,many=True)
            return Response({"status": "success", "game": serializer.data,"players":playerSerializer.data}, status=status.HTTP_200_OK)  
        else:  
            return Response({"status": "error", "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

exitTime = 60 #Si en 1 minuto el jugador no hace peticiones a la mesa, se saca automaticamente de ella
moveTime = 20
exitTable = 40
exitTable2 = 10
fgTime = 10
percent = 10
max_passes_d6 = 3
max_passes_d9 = 5

@api_view(['GET',])
def getPlayer(request,id):
    result = DominoGame.objects.get(id=id)
    serializer =PlayerSerializer(result)
    return Response({'status': 'success', "player":serializer.data,}, status=200)

@api_view(['GET',])
def login(request,alias,email,photo_url,name):
    player,created = Player.objects.get_or_create(alias=alias)
    if created:
        player.email = email
        player.photo_url = photo_url
        player.name = name
        try:
            bank = Bank.objects.get(id=1)
        except ObjectDoesNotExist:
            bank = Bank.objects.create()
        player.coins = 100
        bank.balance-=100
        bank.created_coins+=100
        bank.save()
    player.lastTimeInSystem = timezone.now()
    player.save()
    serializer =PlayerSerializer(player)
    return Response({'status': 'success', "player":serializer.data}, status=200)        


@api_view(['GET',])
def getAllGames(request,alias):
    needUpdate = False
    try:
        player = Player.objects.get(alias=alias)
    except ObjectDoesNotExist:
        return Response ({'status': 'error'},status=400)    
    player.lastTimeInSystem = timezone.now()
    player.save()
    game_id = -1
    playerSerializer = PlayerSerializer(player)
    if needUpdate:
        return Response({'status': 'success', "games":[],"player":playerSerializer.data,"game_id":game_id,"update":needUpdate}, status=200)
    result = DominoGame.objects.all()
    for game in result:
        inGame = checkPlayersTimeOut1(game,alias)
        if inGame:
            game_id = game.id
    serializer =GameSerializer(result,many=True)
    return Response({'status': 'success', "games":serializer.data,"player":playerSerializer.data,"game_id":game_id,"update":needUpdate}, status=200)

@api_view(['GET',])
def getGame(request,game_id,alias):
    result = DominoGame.objects.get(id=game_id)
    serializer = GameSerializer(result)
    players = playersCount(result)
    for player in players:
        if player.alias == alias:
            player.lastTimeInSystem = timezone.now()
            player.save()
        else:
            diff_time = timezone.now() - player.lastTimeInSystem
            diff_time2 = timezone.now()- result.start_time
            if(diff_time.seconds >= exitTable) and result.status != "ru" and result.status != "fi" and result.status != "fg":
                exitPlayer(result,player,players,len(players))    
            elif result.status == "fg" and (diff_time.seconds >= exitTable2) and (diff_time2.seconds >= fgTime):
                exitPlayer(result,player,players,len(players))           
    playerSerializer = PlayerSerializer(players,many=True)
    return Response({'status': 'success', "game":serializer.data,"players":playerSerializer.data}, status=200)

@api_view(['GET',])
def setWinner(request,game_id,winner):
    game = DominoGame.objects.get(id=game_id)
    game.winner = winner
    game.save()
    return Response({'status': 'success'}, status=200)

@api_view(['GET',])
def setStarter(request,game_id,starter):
    game = DominoGame.objects.get(id=game_id)
    game.starter = starter
    game.save()
    return Response({'status': 'success'}, status=200)

@api_view(['GET',])
def setWinnerStarter(request,game_id,winner,starter):
    game = DominoGame.objects.get(id=game_id)
    game.starter = starter
    game.winner = winner
    game.save()
    return Response({'status': 'success'}, status=200)

@api_view(['GET',])
def setWinnerStarterNext(request,game_id,winner,starter,next_player):
    game = DominoGame.objects.get(id=game_id)
    game.starter = starter
    game.winner = winner
    game.next_player = next_player
    game.save()
    return Response({'status': 'success'}, status=200)

@api_view(['GET',])
def getPlayer(request,alias):
    try:
        player = Player.objects.get(alias=alias)
    except ObjectDoesNotExist:
        return Response ({'status': 'error'},status=400)
    serializer = PlayerSerializer(player)
    return Response({'status': 'success', "player":serializer.data}, status=200)

@api_view(['GET',])
def createGame(request,alias,variant):
    try:
        player1 = Player.objects.get(alias=alias)
    except ObjectDoesNotExist:
        return Response ({'status': 'error'},status=400)
    player1.tiles = ""
    player1.lastTimeInSystem = timezone.now()
    player1.save()
    game = DominoGame.objects.create(player1=player1,variant=variant)
    game.lastTime1 = timezone.now()
    updateLastPlayerTime(game,alias)
    game.created_time = timezone.now()
    game.save()
    serializer = GameSerializer(game)
    players = [player1]
    playerSerializer = PlayerSerializer(players,many=True)
    return Response({'status': 'success', "game":serializer.data,"players":playerSerializer.data}, status=200)

@api_view(['GET',])
def joinGame(request,alias,game_id):
    try:
        player = Player.objects.get(alias=alias)
    except ObjectDoesNotExist:
        return Response ({'status': 'error'},status=400)
    player.lastTimeInSystem = timezone.now()
    player.save()
    game = DominoGame.objects.get(id=game_id)
    joined,players = checkPlayerJoined(player,game)
    if joined != True:
        if game.player1 is None:
            game.player1 = player
            joined = True
            players.insert(0,player)
        elif game.player2 is None:
            game.player2 = player
            joined = True
            players.insert(1,player)
        elif game.player3 is None :
            game.player3 = player
            joined = True
            players.insert(2,player)
        elif game.player4 is None:
            game.player4 = player
            joined = True
            players.insert(3,player)

    if joined == True:
        if game.inPairs:
            if len(players) == 4 and game.status != "ru":
               game.status = "ready"
            elif game.status != "ru":
                game.status = "wt"
        else:                
            if len(players) >= 2 and game.status != "ru":
                game.status = "ready"
            elif game.status != "ru":
                game.status = "wt"    
        #updateLastPlayerTime(game,alias)
        game.save()    
        serializerGame = GameSerializer(game)
        playerSerializer = PlayerSerializer(players,many=True)
        return Response({'status': 'success', "game":serializerGame.data,"players":playerSerializer.data}, status=200)
    else:
        return Response({'status': 'Full players', "game":None}, status=300)

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

@api_view(['GET',])
def clearGames(request):
    DominoGame.objects.all().delete()
    return Response({'status': 'success', "message":'All games deleted'}, status=200)

@api_view(['GET',])
def cleanPlayers(request):
    Player.objects.all().delete()
    return Response({'status': 'success', "message":'All players deleted'}, status=200)

def checkingMove(game):
    while game.status == 'ru':
        game.hours_active+=1
        game.save()
        time.sleep(1)

@api_view(['GET',])
def startGame(request,game_id):
    game = DominoGame.objects.get(id=game_id)
    if game.status != "wt":
        players = playersCount(game)
        if game.status != "fi":
            for player in players:
                if player.isPlaying == False:
                    player.isPlaying = True
                    player.save()
        players_ru = list(filter(lambda p: p.isPlaying,players))        
        n = len(players_ru)
        if game.starter == -1 or game.starter >= n:
            game.next_player = random.randint(0,n-1)
            game.starter = game.next_player
        else:
            if players[game.starter].alias != players_ru[game.starter].alias:
                game.starter = getPlayerIndex(players_ru,players[game.starter])
            game.next_player = game.starter
        if game.inPairs and game.winner != 4:
            if game.starter == 0 or game.starter == 2:
                game.winner = 5
            else:
                game.winner = 6    
        #game.winner=-1
            
        game.board = ''
        if game.perPoints and (game.status =="ready" or game.status =="fg"):
            game.scoreTeam1 = 0
            game.scoreTeam2 = 0
            for player in players:
                player.points = 0
            game.rounds = 0    
            
        shuffle(game,players_ru)          
        game.status = "ru"
        game.start_time = timezone.now()
        game.leftValue = -1
        game.rightValue = -1
        game.lastTime1 = None
        game.lastTime2 = None
        game.lastTime3 = None
        game.lastTime4 = None
        game.save()
        serializerGame = GameSerializer(game)
        playerSerializer = PlayerSerializer(players,many=True)
        return Response({'status': 'success', "game":serializerGame.data,"players":playerSerializer.data}, status=200)
    return Response ({'status': 'error'},status=400)

@api_view(['GET',])
def getBank(request):
    bank = Bank.objects.all()
    serializerBank = BankSerializer(bank,many=True)
    return Response({'status': 'success', "bank":serializerBank.data}, status=200)

def movement(game,player,players,tile):
    players_ru = list(filter(lambda p: p.isPlaying, players))
    n = len(players_ru)
    w = getPlayerIndex(players_ru,player)
    alias = player.alias
    isPass = isPass(tile)   
    if isMyTurn(game.board,w,game.starter,n) == False or isPlayingTile(game,tile) or noCorrect(game,tile) or (isPass and (game.status == 'fi' or game.status == 'fg')):
        return 
    if isPass == False:
        isCapicua = False
        if game.perPoints:
            isCapicua = checkCapicua(game,tile)
        updateSides(game,tile)
        tiles_count,tiles = updateTiles(player,tile)
        player.tiles = tiles
        player.save()
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
                updateAllPoints(game,players,w,isCapicua)
            else:
                updatePlayersData(game,players,w,"fi")                                        
        else:
            game.next_player = (w+1) % n 
    elif checkClosedGame1(game,n):
        winner = getWinner(players,game.inPairs,game.variant)
        game.status = 'fg'
        game.start_time = timezone.now()
        game.winner = winner
        if game.perPoints:
            game.rounds+=1
        if winner < 4:
            if game.startWinner:
                game.starter = winner
                game.next_player = winner
            else:
                game.starter = (game.starter+1)%n
                game.next_player = game.starter        
        if game.perPoints and winner < 4:
            updateAllPoints(game,players,winner)
        elif game.perPoints and winner == 4:
            game.status = "fi"
            if game.startWinner and (game.lostStartInTie != True or game.inPairs == False):
                game.next_player = game.starter
            else:    
                game.starter = (game.starter+1)%n
                game.next_player = game.starter
        else:
            updatePlayersData(game,players,winner,"fi")                
    else:
        if game.payPassValue > 0:
            updatePassCoins(w,game,players)
        game.next_player = (w+1) % n
    game.board += (tile+',')
    #updateLastPlayerTime(game,alias)        

def isPlayingTile(game,tile):
    if isPass(tile):
        return False
    tiles = game.board.split(',')
    rtile = rTile(tile)
    for t in tiles:
        if t == tile or t == rtile:
            return True
    return False    

def noCorrect(game,tile):
    values = tile.split('|')
    val0 = int(values[0])
    if val0 == -1 or (game.leftValue == -1 and game.rightValue == -1):
        return False
    val1 = int(values[1])
    if game.leftValue == val0 or game.leftValue == val1 or game.rightValue == val0 or game.rightValue == val1:
        return False
    return True

def rTile(tile):
    values = tile.split('|')
    return (values[1]+"|"+values[0])

def updatePlayersData(game,players,w,status):
    try:
        bank = Bank.objects.get(id=1)
    except ObjectDoesNotExist:
        bank = Bank.objects.create()
    bank_coins = 0
    n = len(players)
    if game.inPairs:
        for i in range(n):
            if i == w or i == ((w+2)%4):
                players[i].dataWins+=1
                if game.payWinValue > 0:
                    bank_coins = int(game.payWinValue*percent/100)
                    bank.datas_coins+=bank_coins
                    player_coins = (game.payWinValue-bank_coins)
                    bank.balance+=(bank_coins)
                    players[i].coins+= player_coins       
                if status == "fg":
                    players[i].matchWins+=1
                    if game.payMatchValue > 0:
                        bank_coins = int(game.payMatchValue*percent/100)
                        bank.matches_coins+=bank_coins
                        player_coins = (game.payMatchValue-bank_coins)
                        bank.balance+=(bank_coins)
                        players[i].coins+= player_coins
                players[i].save()
            else:
                players[i].dataLoss+=1
                if game.payWinValue > 0:
                    players[i].coins-=game.payWinValue
                if status == "fg":
                    players[i].matchLoss+=1
                    if game.payMatchValue > 0:
                        players[i].coins-=game.payMatchValue
                players[i].save()
    else:
        for i in range(n):
            if i == w:
                players[i].dataWins+=1
                bank_coins = int(game.payWinValue*percent/100)*(n-1)
                bank.datas_coins+=bank_coins
                player_coins = (game.payWinValue*(n-1)-bank_coins)
                bank.balance+=(bank_coins)
                players[i].coins+= player_coins
                if game.payWinValue > 0:
                    players[i].coins+=game.payWinValue
                if status == "fg":
                    players[i].matchWins+=1
                    if game.payMatchValue > 0:
                        players[i].coins+=game.payMatchValue
                players[i].save()
            else:
                players[i].dataLoss+=1
                if game.payWinValue > 0:
                    players[i].coins-=game.payWinValue
                if status == "fg":
                    players[i].matchLoss+=1
                    if game.payMatchValue > 0:
                        players[i].coins-=game.payMatchValue
                players[i].save()                                    
    bank.save()

def updatePassCoins(pos,game,players):
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
                        players[pos].coins-=game.payPassValue
                        players[pos1].coins+=game.payPassValue
                        players[pos].save()
                        players[pos1].save()
                    else:
                        pos1 = pos - prev
                        players[pos].coins-=game.payPassValue
                        players[pos1].coins+=game.payPassValue
                        players[pos].save()
                        players[pos1].save()
                elif prev == 2 and game.inPairs == False:
                    if (pos - 2) < 0:
                        pos1 = pos + (n-prev)
                        players[pos].coins-=game.payPassValue
                        players[pos1].coins+=game.payPassValue
                        players[pos].save()
                        players[pos1].save()
                    else:        
                        pos1 = pos - prev
                        players[pos].coins-=game.payPassValue
                        players[pos1].coins+=game.payPassValue
                        players[pos].save()
                        players[pos1].save()
                break                            

@api_view(['GET',])
def move(request,game_id,alias,tile):
    try:
        with transaction.atomic():
            game = DominoGame.objects.select_for_update().get(id=game_id)
            players = playersCount(game)
            players_ru = list(filter(lambda p: p.isPlaying,players))
            for p in players:
                if p.alias == alias:
                    player = p
            movement(game,player,players_ru,tile)
            game.save()
            return Response({'status': 'success'}, status=200)
    except Exception as e:        
        return Response({'status': str(e)}, status=404)    

@api_view(['GET',])
def exitGame(request,game_id,alias):
    game = DominoGame.objects.get(id=game_id)
    player = Player.objects.get(alias=alias)
    players = playersCount(game)
    players_ru = list(filter(lambda p: p.isPlaying,players))
    exited = exitPlayer(game,player,players_ru,len(players))
    if exited:
        return Response({'status': 'success', "message":'Player exited'}, status=200)
    return Response({'status': 'error', "message":'Player no found'}, status=300)

@api_view(['GET',])
def setPatner(request,game_id,alias):
    game = DominoGame.objects.get(id=game_id)
    players = playersCount(game)
    for player in players:
        if player.alias == alias:
            patner = player
            break
    aux = game.player3
    if game.player2.alias == alias:
        game.player2 = aux
        game.player3 = patner
    elif game.player4.alias == alias:
        game.player4 = aux
        game.player3 = patner
    game.save()    
    return Response({'status': 'success'}, status=200)         

@api_view(['GET',])
def rechargeBalance(request,alias,coins):
    player = Player.objects.get(alias=alias)
    player.coins+=coins
    try:
        bank = Bank.objects.get(id=1)
    except ObjectDoesNotExist:
        bank = Bank.objects.create()
    bank.balance+=coins
    bank.buy_coins+=coins
    bank.save()    
    player.save()
    return Response({'status': 'success', "message":'Balance recharged'}, status=200)

@api_view(['GET',])
def payment(request,alias,coins):
    player = Player.objects.get(alias=alias)
    player.coins-=coins
    try:
        bank = Bank.objects.get(id=1)
    except ObjectDoesNotExist:
        bank = Bank.objects.create()
    bank.balance-=coins
    bank.extracted_coins+=coins
    bank.save()    
    player.save()
    return Response({'status': 'success', "message":'Payment done!!'}, status=200)

def exitPlayer(game,player,players,totalPlayers):
    exited = False
    pos = getPlayerIndex(players,player)
    isStarter = (game.starter == pos)
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
            if (game.status == "ru" or game.status == "fi") and (game.payWinValue > 0 or game.payMatchValue > 0):
                loss_coins = (game.payWinValue+game.payMatchValue)
                coins = loss_coins
                try:
                    bank = Bank.objects.get(id=1)
                except ObjectDoesNotExist:
                    bank = Bank.objects.create()
                bank_coins = int(coins*percent/100)
                bank.balance+=bank_coins
                coins -= bank_coins
                if game.inPairs:
                    players[(pos+1)%4].coins+=coins/2
                    players[(pos+3)%4].coins+=coins/2
                    players[(pos+1)%4].save()
                    players[(pos+3)%4].save()     
                else:
                    n = len(players)-1
                    for p in players:
                        if p.alias != player.alias:
                            p.coins+= (coins/n)
                            p.save()
                player.coins-=loss_coins            
                bank.save()                               
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
                if game.winner < 4 and game.winner > pos:
                    game.winner-=1
            player.isPlaying = False
        else:
            if totalPlayers <= 2 or game.inPairs:
                game.status = "wt"
                game.starter = -1
        reorderPlayers(game,player)                                                       
        player.save()
        game.save()    
    return exited    

def reorderPlayers(game,player):
    k = 0
    players = playersCount(game)
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
            k+=1

def updateTeamScore(game, winner, players, sum_points):
    n = len(players)
    if winner == 0 or winner == 2:
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
        updatePlayersData(game,players,winner,"fg")
        game.start_time = timezone.now()
        game.winner = 5 #Gano el equipo 1
    elif game.scoreTeam2 >= game.maxScore:
        game.status="fg"
        updatePlayersData(game,players,winner,"fg")
        game.start_time = timezone.now()
        game.winner = 6 #Gano el equipo 2
    else:
        updatePlayersData(game,players,winner,"fi")
        game.status="fi"    
    
def updateAllPoints(game,players,winner,isCapicua=False):
    sum_points = 0
    n = len(players)
    if game.sumAllPoints:
        for i in range(n):
            sum_points+=totalPoints(players[i].tiles)
            if isCapicua and game.capicua:
                sum_points*=2     
        if game.inPairs:
            updateTeamScore(game,winner,players,sum_points)                
        else:
            players[winner].points+=sum_points
            players[winner].save()
            if players[winner].points >= game.maxScore:
                game.status = "fg"
                updatePlayersData(game,players,winner,"fg")
            else:
                game.status = "fi"
                updatePlayersData(game,players,winner,"fi")                              
    else:#En caso en que se sumen los puntos solo de los perdedores
        for i in range(n):
            if i != winner:
                sum_points+=totalPoints(players[i].tiles)
        if game.inPairs:
            patner = (winner+2)%4
            sum_points-=totalPoints(players[patner].tiles)
            if isCapicua and game.capicua:
                sum_points*=2
            updateTeamScore(game,winner,players,sum_points)
        else:
            if isCapicua and game.capicua:
                sum_points*=2
            players[winner].points+=sum_points
            players[winner].save()
            if players[winner].points >= game.maxScore:
                game.status = "fg"
                updatePlayersData(game,players,winner,"fg")
            else:
                game.status = "fi"
                updatePlayersData(game,players,winner,"fi")    

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
    values = tile.split('|')
    inverse = (values[1]+'|'+values[0])
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
            
def checkClosedGame(game,players):
    for player in players:
        tiles = player.tiles.split(',')
        for tile in tiles:
            values = tile.split('|')
            val0 = int(values[0])
            val1 = int(values[1])
            if val0 == game.leftValue or val0 == game.rightValue or val1 == game.leftValue or val1 == game.rightValue:
                return False
    return True    

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
        player = Player.objects.get(id=players[i].id)
        player.tiles = ""
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

def checkPlayersTimeOut(game):
    n = 0
    players = []
    if game.player1 is not None:
        if game.lastTime1 is not None:
            timediff = timezone.now() - game.lastTime1
        if game.lastTime1 is None or timediff.seconds > exitTime:
            players.append(game.player1)
            game.player1 = None
        else:
            n+=1        
    if game.player2 is not None:
        if game.lastTime2 is not None:
            timediff = timezone.now() - game.lastTime2
        if game.lastTime2 is None or timediff.seconds > exitTime:
            players.append(game.player2)
            game.player2 = None
        else:
            n+=1    
    if game.player3 is not None:
        if game.lastTime3 is not None:
            timediff = timezone.now() - game.lastTime3
        if game.lastTime3 is None or timediff.seconds > exitTime:
            players.append(game.player3)
            game.player3 = None
        else:
            n+=1    
    if game.player4 is not None:
        if game.lastTime4 is not None:
            timediff = timezone.now() - game.lastTime4
        if game.lastTime4 is None or timediff.seconds > exitTime:
            players.append(game.player4)
            game.player4 = None
        else:
            n+=1
    if n < 2 or (n < 4 and game.inPairs):
        game.status = "wt"
        game.starter=-1
    for player in players:
        player.tiles = ""
        player.points = 0
        player.save()    
    game.save()                                 

def checkPlayersTimeOut1(game,alias):
    n = 0
    players = []
    inGame = False
    diff_time2 = timezone.now()- game.start_time
    if game.player1 is not None:
        if game.player1.lastTimeInSystem is not None:
            timediff = timezone.now() - game.player1.lastTimeInSystem
            if timediff.seconds > exitTime and game.status != "ru" and game.status != "fi" and game.status != "fg":
                players.append(game.player1)
                game.player1 = None
            elif game.status == "fg" and (timediff.seconds >= exitTable2) and (diff_time2.seconds >= fgTime):
                players.append(game.player1)
                game.player1 = None    
            else:
                if game.player1.alias == alias:
                    inGame = True
                n+=1
        else:
            if game.player1.alias == alias:
                inGame = True
            n+=1                
    if game.player2 is not None:
        if game.player2.lastTimeInSystem is not None:
            timediff = timezone.now() - game.player2.lastTimeInSystem
            if timediff.seconds > exitTime and game.status != "ru" and game.status != "fg" and game.status != "fi":
                players.append(game.player2)
                game.player2 = None
            elif game.status == "fg" and (timediff.seconds >= exitTable2) and (diff_time2.seconds >= fgTime):
                players.append(game.player2)
                game.player2 = None     
            else:
                if game.player2.alias == alias:
                    inGame = True
                n+=1
        else:
            if game.player2.alias == alias:
                inGame = True
            n+=1            
    if game.player3 is not None:
        if game.player3.lastTimeInSystem is not None:
            timediff = timezone.now() - game.player3.lastTimeInSystem
            if timediff.seconds > exitTime and game.status != "fg" and game.status != "ru" and game.status != "fi":
                players.append(game.player3)
                game.player3 = None
            elif game.status == "fg" and (timediff.seconds >= exitTable2) and (diff_time2.seconds >= fgTime):
                players.append(game.player3)
                game.player3 = None     
            else:
                if game.player3.alias == alias:
                    inGame = True
                n+=1
        else:
            if game.player3.alias == alias:
                inGame = True
            n+=1            
    if game.player4 is not None:
        if game.player4.lastTimeInSystem is not None:
            timediff = timezone.now() - game.player4.lastTimeInSystem
            if timediff.seconds > exitTime and game.status != "ru" and game.status != "fi" and game.status != "fg":
                players.append(game.player4)
                game.player4 = None
            elif game.status == "fg" and (timediff.seconds >= exitTable2) and (diff_time2.seconds >= fgTime):
                players.append(game.player4)
                game.player4 = None     
            else:
                if game.player4.alias == alias:
                    inGame = True
                n+=1
        else:
            if game.player4.alias == alias:
                inGame = True
            n+=1        
    if n < 2 or (n < 4 and game.inPairs):
        game.status = "wt"
        game.starter=-1
        game.board = ""
    for player in players:
        player.tiles = ""
        player.points = 0
        player.isPlaying = False
        player.save()        
    game.save()
    return inGame

def updateLastPlayerTime(game,alias):
    if game.player1 is not None and game.player1.alias == alias:
        game.lastTime1 = timezone.now()
    elif game.player2 is not None and game.player2.alias == alias:
        game.lastTime2 = timezone.now()
    if game.player3 is not None and game.player3.alias == alias:
        game.lastTime3 = timezone.now()
    if game.player4 is not None and game.player4.alias == alias:
        game.lastTime4 = timezone.now()  

def takeRandomTile(tiles):
    list_tiles = tiles.split(',')
    i = random.randint(0,len(list_tiles)-1)
    return list_tiles[i]

def takeRandomCorrectTile(tiles,left,right):
    list_tiles = tiles.split(',')
    random.shuffle(list_tiles)
    for tile in list_tiles:
        values = tile.split('|')
        val1 = int(values[0])
        val2 = int(values[1])
        if val1 == left or val1 == right or val2 == left or val2 == right:
            return tile
    return "-1|-1"     

def previusPlayer(pos,n):
    if pos == 0: 
        return n-1
    return pos-1

def getLastPlayerMoveTime(game,pos):
    if pos == 0:
        return game.lastTime1
    elif pos == 1:
        return game.lastTime2
    elif pos == 2:
        return game.lastTime3
    else:
        return game.lastTime4
    
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


