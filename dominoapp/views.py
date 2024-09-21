from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status 
from .models import Player
from .serializers import PlayerSerializer
from .serializers import MyPlayerSerializer
from .models import DominoGame
from .serializers import GameSerializer
from django.shortcuts import get_object_or_404 
from rest_framework.decorators import api_view
from rest_framework import generics
from django.utils import timezone
import random

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
            player1,created = Player.objects.get_or_create(alias=alias)
            player1.tiles = ""
            player1.points=0
            player1.save()
            players = [player1]
            data = serializer.validated_data
            data['player1']=player1
            serializer.save(player1=data['player1'])
            playerSerializer = PlayerSerializer(players,many=True)
            return Response({"status": "success", "game": serializer.data,"players":playerSerializer.data}, status=status.HTTP_200_OK)  
        else:  
            return Response({"status": "error", "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

exitTime = 6000 #Si en 100 minutos el jugador no hace peticiones a la mesa, se saca automaticamente de ella
moveTime = 15

@api_view(['GET',])
def getAllGames(request,alias):
    result = DominoGame.objects.all()
    player = Player.objects.get(alias=alias)
    player.lastTimeInSystem = timezone.now()
    for game in result:
        checkPlayersTimeOut(game)
    serializer =GameSerializer(result,many=True)
    return Response({'status': 'success', "games":serializer.data}, status=200)

@api_view(['GET',])
def getGame(request,game_id,alias):
    result = DominoGame.objects.get(id=game_id)
    serializer = GameSerializer(result)
    players = playersCount(result)
    for player in players:
        if player.alias == alias:
            player.lastTimeInSystem = timezone.now()
    #if result.status == 'ru':
    #   player = players[result.next_player]
    #   lastMoveTime = getLastMoveTime(result,players[result.next_player])
    #   prevPlayer = previusPlayer(result.next_player,len(players))
    #   prevPlayerTime = getLastMoveTime(result,players[prevPlayer])
    #   if len(result.board) == 0:
    #       diff_time = timezone.now()-result.start_time
    #       if diff_time.seconds >= (result.moveTime+1) and lastMoveTime is None:
    #            tile = takeRandomTile(player.tiles)
    #            movement(result,player,players,tile)                
    #   elif lastMoveTime is not None:
    #       diff_time1 = timezone.now() - prevPlayerTime
    #       diff_time = timezone.now() - lastMoveTime
    #       if diff_time.seconds >= (result.moveTime+1) and diff_time1.seconds >= (result.moveTime+1):
    #           tile = takeRandomCorrectTile(player.tiles,result.leftValue,result.rightValue)
    #           movement(result,player,players,tile)
    #   else:
    #       diff_time1 = timezone.now() - prevPlayerTime
    #       if diff_time.seconds >= (result.moveTime+1):
    #            tile = takeRandomCorrectTile(player.tiles,result.leftValue,result.rightValue)
    #            movement(result,player,players,tile)              
    #checkPlayersTimeOut(result)
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
    player = Player.objects.get_or_create(alias=alias)
    serializer = PlayerSerializer(player)
    return Response({'status': 'success', "player":serializer.data}, status=200)

@api_view(['GET',])
def createGame(request,alias,variant):
    player1,created = Player.objects.get_or_create(alias=alias)
    player1.tiles = ""
    player1.save()
    game = DominoGame.objects.create(player1=player1,variant=variant)
    game.lastTime1 = timezone.now()
    updateLastPlayerTime(game,alias)
    game.save()
    serializer = GameSerializer(game)
    players = [player1]
    playerSerializer = PlayerSerializer(players,many=True)
    return Response({'status': 'success', "game":serializer.data,"players":playerSerializer.data}, status=200)

@api_view(['GET',])
def joinGame(request,alias,game_id):
    player,created = Player.objects.get_or_create(alias=alias)
    player.tiles = ""
    player.points = 0
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
            if len(players) == 4:
               game.status = "ready"
            else:
                game.status = "wt"
        else:                
            if len(players) >= 2:
                game.status = "ready"
            else:
                game.status = "wt"    
        updateLastPlayerTime(game,alias)
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

@api_view(['GET',])
def startGame(request,game_id):
    game = DominoGame.objects.get(id=game_id)
    players = playersCount(game)
    n = len(players)
    shuffle(game,players)
    if game.starter == -1 or game.starter >= n:
        game.next_player = random.randint(0,n-1)
        game.starter = game.next_player
    else:
        game.next_player = game.starter
    if game.inPairs and game.winner != 4:
        if game.starter == 0 or game.starter == 2:
            game.winner = 5
        else:
            game.winner = 6    
    #game.winner=-1
        
    game.board = ''
    if game.perPoints and (game.status =="ready" or game.status =="fg") and game.inPairs:
        game.scoreTeam1 = 0
        game.scoreTeam2 = 0
    if game.status == "fg":
        game.rounds = 0        
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

@api_view(['POST',])
def startGame1(request,game_id):
    game = DominoGame.objects.get(id=game_id)
    players = playersCount(game)
    shuffle(game,players)
    if game.starter == -1:
        game.next_player = random.randint(0,len(players)-1)
        game.starter = game.next_player
    else:
        game.next_player = game.starter
    if game.inPairs and game.winner != 4:
        if game.starter == 0 or game.starter == 2:
            game.winner = 5
        else:
            game.winner = 6    
    #game.winner=-1
        
    game.board = ''
    if game.perPoints and (game.status =="ready" or game.status =="fg") and game.inPairs:
        game.scoreTeam1 = 0
        game.scoreTeam2 = 0
    if game.status == "fg":
        game.rounds = 0        
    game.status = "ru"
    game.start_time = timezone.now()
    game.leftValue = -1
    game.rightValue = -1
    game.save()
    while True:
        if game.status != "ru":
            break
        player = players[game.next_player]
        if len(game.board) == 0:
            diff_time = timezone.now() - game.start_time
            if diff_time >= moveTime:
                tile = takeRandomTile(player.tiles)
                movement(game,player,players,tile)
        else:
            prevIndex = previusPlayer(game.next_player)
            diff_time = timezone.now() - getLastPlayerMoveTime(game,prevIndex)
            if diff_time >= moveTime:
                tile = takeRandomCorrectTile(player.tiles,game.leftValue,game.rightValue)
                movement(game,player,players,tile)                

def movement(game,player,players,tile):
    n = len(players)
    w = getPlayerIndex(players,player)
    alias = player.alias   
    if isMyTurn(game.board,w,game.starter,n) == False:
        return 
    if isPass(tile) == False:
        isCapicua = False
        if game.perPoints:
            isCapicua = checkCapicua(game,tile)
        updateSides(game,tile)
        tiles_count,tiles = updateTiles(player,tile)
        player.tiles = tiles
        player.save()
        if tiles_count == 0:
            game.rounds+=1
            game.status = 'fg'
            if game.startWinner:
                game.starter = w
                game.next_player = w
            else:
                game.starter = (game.starter+1)%n
                game.next_player = game.starter    
            game.winner = w
            if game.perPoints:
                updateAllPoints(game,players,w,isCapicua)                                    
        else:
            game.next_player = (w+1) % n 
    elif checkClosedGame1(game,n):
        winner = getWinner(players)
        game.rounds+=1
        game.status = 'fg'
        game.winner = winner
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
        game.next_player = (w+1) % n
    game.board += (tile+',')
    updateLastPlayerTime(game,alias)        

@api_view(['GET',])
def move(request,game_id,alias,tile):
    game = DominoGame.objects.get(id=game_id)
    players = playersCount(game)
    for p in players:
        if p.alias == alias:
            player = p
    movement(game,player,players,tile)
    game.save()
    return Response({'status': 'success'}, status=200)

@api_view(['GET',])
def exitGame(request,game_id,alias):
    game = DominoGame.objects.get(id=game_id)
    player = Player.objects.get(alias=alias)
    players = playersCount(game)
    exited = exitPlayer(game,player)
    if exited:
        player.points = 0
        player.tiles = ""
        if len(players) <= 2 or game.inPairs:
            game.status = "wt"
        player.save()
        game.save()
        return Response({'status': 'success', "message":'Player exited'}, status=200)
    return Response({'status': 'error', "message":'Player no found'}, status=300)

def exitPlayer(game,player):
    exited = False
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
    return exited    

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
        game.winner = 5 #Gano el equipo 1
    elif game.scoreTeam2 >= game.maxScore:
        game.status="fg"
        game.winner = 6 #Gano el equipo 2
    else:
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
            else:
                game.status = "fi"                              
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
            else:
                game.status = "fi"    

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

def getWinner(players):
    i = 0
    min = 1000
    res = -1
    for player in players:
        pts = totalPoints(player.tiles)
        if pts < min:
            min = pts
            res = i
        elif pts == min:
            res = 4
        i+=1    
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