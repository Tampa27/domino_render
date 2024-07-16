from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status 
from .models import Player
from .serializers import PlayerSerializer
from .models import DominoGame
from .serializers import GameSerializer
from django.shortcuts import get_object_or_404 
from rest_framework.decorators import api_view
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
    
class PlayersView(APIView):
    def get(self, request, *args, **kwargs):  
        result = Player.objects.all()  
        serializers = PlayerSerializer(result, many=True)  
        return Response({'status': 'success', "players":serializers.data}, status=200)  

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
    return Response({'status': 'success', "games":serializer.data,"players":playerSerializer.data}, status=200)


@api_view(['GET',])
def createGame(request,alias,variant):
    player1,created = Player.objects.get_or_create(alias=alias)
    game = DominoGame.objects.create(player1=player1,variant=variant)
    game.save()
    serializer = GameSerializer(game)
    players = [player1]
    playerSerializer = PlayerSerializer(players,many=True)
    return Response({'status': 'success', "game":serializer.data,"players":playerSerializer.data}, status=200)

@api_view(['GET',])
def joinGame(request,alias,game_id):
    player,created = Player.objects.get_or_create(alias=alias)
    game = DominoGame.objects.get(id=game_id)
    joined = False
    joined_count = 1
    players = [game.player1]
    if game.player2 is None:
        game.player2 = player
        joined = True
        joined_count+=1
        game.status = "ready"
        players.append(game.player2)
    elif game.player3 is None:
        game.player3 = player
        joined = True
        joined_count+=2
        game.status = "ready"
        players.append(game.player2)
        players.append(game.player3)
    elif game.player4 is None:
        game.player4 = player
        joined = True
        joined_count+=3
        game.status = "ready"
        players.append(game.player2)
        players.append(game.player3)
        players.append(game.player4)

    if joined == True:
        game.save()    
        serializerGame = GameSerializer(game)
        playerSerializer = PlayerSerializer(players,many=True)
        return Response({'status': 'success', "game":serializerGame.data,"players":playerSerializer.data}, status=200)
    else:
        return Response({'status': 'Full players', "game":None}, status=300)

@api_view(['GET',])
def startGame(request,game_id):
    game = DominoGame.objects.get(id=game_id)
    players = playersCount(game)
    shuffle(game.variant,players)
    if game.starter == -1:
        game.next_player = random.randint(0,len(players)-1)
        game.starter = game.next_player
    else:
        game.next_player = game.starter
    game.winner=-1    
    game.board = ''    
    game.status = "ru"
    game.start_time = timezone.now()
    game.save()
    serializerGame = GameSerializer(game)
    playerSerializer = PlayerSerializer(players,many=True)
    return Response({'status': 'success', "game":serializerGame.data,"players":playerSerializer.data}, status=200)

@api_view(['GET',])
def move(request,game_id,alias,tile):
    game = DominoGame.objects.get(id=game_id)
    players = playersCount(game)
    player = Player.objects.get(alias=alias)
    n = len(players)
    if isPass(tile):
        if checkClosedGame(game,n):
            winner = getWinner(players)
            game.status = 'fi'
            game.winner = winner
    else:
        tiles_count,tiles = updateTiles(player,tile)
        player.tiles = tiles
        player.save()
        w = getPlayerIndex(players,player)
        if tiles_count == 0:
            game.winner = w
            game.starter = w
            game.next_player = w
            game.status = 'fi'
        else:
            game.next_player = (w+1) % n 
    if(game.winner == -1):             
        game.board += (tile+',')
    else:
        game.board += tile        
    game.save()
    serializerGame = GameSerializer(game)
    return Response({'status': 'success', "game":serializerGame.data}, status=200)

def getPlayerIndex(players,player):
    for i in range(len(players)):
        if player.id == players[i].id:
            return i
    return -1

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
            res = 5
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

def shuffle(variant, players):
    tiles = []
    max = 0
    if variant == "d6":
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
        for j in range(max):
            player.tiles+=tiles[i*max+j]
            if j < (max-1):
                player.tiles+=","
        player.save()    
