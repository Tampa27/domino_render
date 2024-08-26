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

@api_view(['GET',])
def getAllGames(request):
    result = DominoGame.objects.all()
    serializer =GameSerializer(result,many=True)
    return Response({'status': 'success', "games":serializer.data}, status=200)

@api_view(['GET',])
def getGame(request,game_id):
    result = DominoGame.objects.get(id=game_id)
    serializer =GameSerializer(result)
    players = playersCount(result)
    playerSerializer = PlayerSerializer(players,many=True)
    return Response({'status': 'success', "game":serializer.data,"players":playerSerializer.data}, status=200)


@api_view(['GET',])
def createGame(request,alias,variant):
    player1,created = Player.objects.get_or_create(alias=alias)
    player1.tiles = ""
    player1.save()
    game = DominoGame.objects.create(player1=player1,variant=variant)
    game.save()
    serializer = GameSerializer(game)
    players = [player1]
    playerSerializer = PlayerSerializer(players,many=True)
    return Response({'status': 'success', "game":serializer.data,"players":playerSerializer.data}, status=200)

@api_view(['GET',])
def joinGame(request,alias,game_id):
    player,created = Player.objects.get_or_create(alias=alias)
    player.tiles = ""
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
        if len(players) >= 2:
            game.status = "ready"
        else:
            game.status = "wt"    
        game.save()    
        serializerGame = GameSerializer(game)
        playerSerializer = PlayerSerializer(players,many=True)
        return Response({'status': 'success', "game":serializerGame.data,"players":playerSerializer.data}, status=200)
    else:
        return Response({'status': 'Full players', "game":None}, status=300)

def checkPlayerJoined(player,game):
    res = False
    players = []
    if game.player1 != None:
        players.append(game.player1)
        if game.player1.alias == player.alias:
            res = True
    if game.player2 != None:
        players.append(game.player2)
        if game.player2.alias == player.alias:
            res = True
    if game.player3 != None:
        players.append(game.player3)
        if game.player3.alias == player.alias:
            res = True
    if game.player4 != None:
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
    shuffle(game,players)
    if game.starter == -1:
        game.next_player = random.randint(0,len(players)-1)
        game.starter = game.next_player
    else:
        game.next_player = game.starter
    game.winner=-1    
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
    serializerGame = GameSerializer(game)
    playerSerializer = PlayerSerializer(players,many=True)
    return Response({'status': 'success', "game":serializerGame.data,"players":playerSerializer.data}, status=200)

@api_view(['GET',])
def move(request,game_id,alias,tile):
    game = DominoGame.objects.get(id=game_id)
    players = playersCount(game)
    for p in players:
        if p.alias == alias:
            player = p
    n = len(players)
    w = getPlayerIndex(players,player)    
    if isPass(tile) == False:
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
                updateAllPoints(game,players,w,isCapicua=checkCapicua(game,tile))
        elif checkClosedGame(game,players):
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
                if game.startWinner:
                    game.next_player = game.starter
                else:
                    game.starter = (game.starter+1)%n
                    game.next_player = game.starter                                    
        else:
            game.next_player = (w+1) % n 
    elif checkClosedGame(game,players):
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
            if game.startWinner:
                game.next_player = game.starter
            else:    
                game.starter = (game.starter+1)%n
                game.next_player = game.starter        
    else:
        game.next_player = (w+1) % n
    game.board += (tile+',')
    updateLastPlayerTime(game,alias)        
    game.save()
    #serializerGame = GameSerializer(game)
    return Response({'status': 'success','count':tiles_count,'tiles':player.tiles}, status=200)

@api_view(['GET',])
def exitGame(request,game_id,alias):
    game = DominoGame.objects.get(id=game_id)
    player = Player.objects.get(alias=alias)
    players = playersCount(game)
    exited = False
    if game.player1 != None and game.player1.alias == player.alias:
        game.player1 = None
        exited = True
    elif game.player2 != None and game.player2.alias == player.alias:
        game.player2 = None
        exited = True
    elif game.player3 != None and game.player3.alias == player.alias:
        game.player3 = None
        exited = True
    elif game.player4 != None and game.player4.alias == player.alias:
        game.player4 = None
        exited = True
    if exited:
        player.points = 0
        player.tiles = ""
        if len(players) <= 2:
            game.status = "wt"
        player.save()
        game.save()
        return Response({'status': 'success', "message":'Player exited'}, status=200)
    return Response({'status': 'error', "message":'Player no found'}, status=300)

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
    total = 0
    list_tiles = tiles.split(',')
    for tile in list_tiles:
        total+=getPoints(tile)
    return total

def getPoints(tile):
    values = tile.split('|')
    return int(values[0])+int(values[1])    

def checkClosedGame(game, playersCount):
    tiles = game.board.split(',')
    lastPasses = 0
    for tile in reversed(tiles):
        if(isPass(tile)):
            lastPasses+=1
            if lastPasses == playersCount-1:
                return True
        elif len(tile) != 0:
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

def updateLastPlayerTime(game,alias):
    if game.player1 != None and game.player1.alias == alias:
        game.lastTime1 = timezone.now()
    elif game.player2 != None and game.player2.alias == alias:
        game.lastTime2 = timezone.now()
    if game.player3 != None and game.player3.alias == alias:
        game.lastTime3 = timezone.now()
    if game.player4 != None and game.player4.alias == alias:
        game.lastTime4 = timezone.now()             

