import os
from rest_framework import serializers
from django.db.models import Q
from .models import Player
from .models import DominoGame, MatchGame, DataGame
from .models import Bank, Marketing, MoveRegister
from dominoapp.utils.game_tools import playersCount, getplayerpoints

class PlayerSerializer(serializers.ModelSerializer):
    alias = serializers.CharField(max_length=32,required=True)
    tiles = serializers.CharField(max_length=32)
    earned_coins = serializers.IntegerField()
    recharged_coins = serializers.IntegerField()
    points = serializers.SerializerMethodField(read_only = True)
    dataWins = serializers.IntegerField()
    dataLoss = serializers.IntegerField()
    matchWins = serializers.IntegerField()
    matchLoss = serializers.IntegerField()
    lastTimeInSystem = serializers.DateTimeField()
    email = serializers.CharField()
    photo_url = serializers.CharField()
    name = serializers.CharField()
    isPlaying = serializers.BooleanField()
    coins = serializers.SerializerMethodField(read_only = True)
    
    def get_points(self, obj: Player) -> int:
        data = DataGame.objects.filter(active=True).filter(
            Q(player1__id = obj.id)|
            Q(player2__id = obj.id)|
            Q(player3__id = obj.id)|
            Q(player4__id = obj.id)
            ).order_by('-id').first()
        if data.player1 is not None and data.player1.id == obj.id:
            return data.match.score_player1
        elif data.player2 is not None and data.player2.id == obj.id:
            return data.match.score_player2
        elif data.player3 is not None and data.player3.id == obj.id:
            return data.match.score_player3
        elif data.player4 is not None and data.player4.id == obj.id:
            return data.match.score_player4
        else:
            return 0

    def get_coins(self, obj: Player) -> int:
        return obj.recharged_coins + obj.earned_coins

    class Meta:
        model = Player
        fields = ('__all__')

    def create(self, validated_data):  
        """ 
        Create and return a new `Player` instance, given the validated data. 
        """  
        return Player.objects.create(**validated_data)  
    def update(self, instance:Player, validated_data):  
        """ 
        
        """  
        instance.alias = validated_data.get('alias', instance.alias)
        instance.tiles = validated_data.get('tiles', instance.tiles)
        instance.dataWins = validated_data.get('dataWins', instance.dataWins)
        instance.dataLoss = validated_data.get('dataLoss', instance.dataLoss)
        instance.matchWins = validated_data.get('matchWins', instance.matchWins)
        instance.matchLoss = validated_data.get('matchLoss', instance.matchLoss)
        instance.lastTimeInSystem = validated_data.get('lastTimeInSystem',instance.lastTimeInSystem)
        instance.email = validated_data.get('email', instance.email)
        instance.photo_url = validated_data.get('photo_url', instance.photo_url)
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        return instance     

class PlayerGameSerializer(serializers.ModelSerializer):
    coins = serializers.SerializerMethodField()
    points = serializers.SerializerMethodField()
    
    def get_coins(self, obj: Player) -> int:
        return obj.earned_coins + obj.recharged_coins
    
    def get_points(self, obj: Player) -> int:
        data = DataGame.objects.filter(active=True).filter(
            Q(player1__id = obj.id)|
            Q(player2__id = obj.id)|
            Q(player3__id = obj.id)|
            Q(player4__id = obj.id)
            ).order_by('-id').first()
        if data.player1 is not None and data.player1.id == obj.id:
            return data.match.score_player1
        elif data.player2 is not None and data.player2.id == obj.id:
            return data.match.score_player2
        elif data.player3 is not None and data.player3.id == obj.id:
            return data.match.score_player3
        elif data.player4 is not None and data.player4.id == obj.id:
            return data.match.score_player4
        else:
            return 0
    
    class Meta:
        model = Player
        fields = ["id", "name", "alias", "lastTimeInSystem", "email", "photo_url", "coins", "tiles", "isPlaying", "points"]

class PlayerLoginSerializer(serializers.ModelSerializer):
    coins = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    
    def get_coins(self, obj: Player) -> int:
        return obj.earned_coins + obj.recharged_coins
    
    def get_url(self, obj: Player) -> str:
        BACKEND_URL = os.getenv("BACKEND_URL", "localhost:8000/v2/api")
        return f"{BACKEND_URL}/refer/?refer_code={obj.referral_code}"
    
    class Meta:
        model = Player
        fields = ["id", "name", "alias", "lastTimeInSystem", "email", "photo_url", "coins", "earned_coins", "recharged_coins", "referral_code", "url"]

class GameCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = DominoGame
        fields = ["variant", "maxScore", "inPairs", "perPoints", "startWinner", "lostStartInTie", "payPassValue", "payWinValue", "payMatchValue", "startAuto", "sumAllPoints", "capicua", "moveTime", "password"]


class GameSerializer(serializers.ModelSerializer):

    class Meta:
        model = DominoGame
        fields = ('__all__')


class GameRetrieveSerializer(serializers.ModelSerializer):
    rounds= serializers.SerializerMethodField()
    status= serializers.SerializerMethodField()
    scoreTeam1= serializers.SerializerMethodField() 
    scoreTeam2 = serializers.SerializerMethodField()
    player1= serializers.SerializerMethodField()
    player2= serializers.SerializerMethodField()
    player3= serializers.SerializerMethodField()
    player4= serializers.SerializerMethodField()
    board= serializers.SerializerMethodField()
    leftValue= serializers.SerializerMethodField()
    rightValue= serializers.SerializerMethodField()
    winner= serializers.SerializerMethodField()
    starter= serializers.SerializerMethodField()
    next_player= serializers.SerializerMethodField()
    lastTime1= serializers.SerializerMethodField()
    lastTime2= serializers.SerializerMethodField()
    lastTime3= serializers.SerializerMethodField()
    lastTime4= serializers.SerializerMethodField()
    start_time= serializers.SerializerMethodField()
    hours_active= serializers.SerializerMethodField()
    
    def get_rounds(self, obj: DominoGame) -> int:
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.match.rounds if data else 0
    
    def get_status(self, obj: DominoGame) -> str:
        latest_match = MatchGame.objects.filter(active=True, domino_game__id=obj.id).order_by('-id').first()
        latest_data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        if latest_match and latest_data:
            return latest_data.status if latest_match.status != 'fg' else latest_match.status
        return 'wt'        
    
    def get_scoreTeam1(self, obj: DominoGame) -> int:
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.match.scoreTeam1 if data else 0
    
    def get_scoreTeam2(self, obj: DominoGame) -> int:
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.match.scoreTeam2 if data else 0
    
    def get_player1(self, obj: DominoGame):
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        player = data.player1.id if data and data.player1 else None
        return player
    
    def get_player2(self, obj: DominoGame):
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        player = data.player2.id if data and data.player2 else None
        return player
    
    def get_player3(self, obj: DominoGame):
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        player = data.player3.id if data and data.player3 else None
        return player
    
    def get_player4(self, obj: DominoGame):
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        player = data.player4.id if data and data.player4 else None
        return player
    
    def get_board(self, obj: DominoGame) -> str:
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.board if data else ""
        
    def get_leftValue(self, obj: DominoGame) -> int:
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.leftValue if data else -1
    
    def get_rightValue(self, obj: DominoGame) -> int:
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.rightValue if data else -1
    
    def get_winner(self, obj: DominoGame):
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.winner if data else -1
    
    def get_starter(self, obj: DominoGame):
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.starter if data else -1
    
    def get_next_player(self, obj: DominoGame):
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.next_player if data else -1
    
    def get_lastTime1(self, obj: DominoGame):
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.lastTime1 if data else obj.created_time
    
    def get_lastTime2(self, obj: DominoGame):
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.lastTime2 if data else obj.created_time
    
    def get_lastTime3(self, obj: DominoGame):
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.lastTime3 if data else obj.created_time
    
    def get_lastTime4(self, obj: DominoGame):
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.lastTime4 if data else obj.created_time
    
    def get_start_time(self, obj: DominoGame):
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.match.start_time if data else obj.created_time
    
    def get_hours_active(self, obj: DominoGame) -> float:
        data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        if data:
            from django.utils import timezone
            delta = timezone.now() - data.match.start_time
            hours = delta.total_seconds() / 3600
            return round(hours, 2)
        return 0.0
    
    class Meta:
        model = DominoGame
        fields = ('__all__')

class ListGameSerializer(serializers.ModelSerializer):
    is_privated = serializers.SerializerMethodField()
    number_player = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_is_privated(self, obj: DominoGame)-> bool:
        return True if obj.password != "" else False
    
    def get_number_player(self, obj: DominoGame) -> int:
        data = DataGame.objects.filter(active= True, match__domino_game__id=obj.id).order_by('-id').first()
        players = playersCount(data)
        return len(players)
    
    def get_start_time(self, obj: DominoGame) -> str:
        data = DataGame.objects.filter(active= True, match__domino_game__id=obj.id).order_by('-id').first()
        return data.match.start_time if data else obj.created_time
    
    def get_status(self, obj: DominoGame) -> str:
        latest_match = MatchGame.objects.filter(active=True, domino_game__id=obj.id).order_by('-id').first()
        latest_data = DataGame.objects.filter(active=True, match__domino_game__id=obj.id).order_by('-id').first()
        if latest_match and latest_data:
            return latest_data.status if latest_match.status != 'fg' else latest_match.status
        return 'wt' 
    
    class Meta:
        model = DominoGame
        fields = ["id", "status", "variant", "start_time", "inPairs", "perPoints", "payPassValue", "payWinValue", "payMatchValue", "maxScore", "created_time", "is_privated", "password", "number_player"]


class MarketingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marketing
        fields = ["image", "text", "url"]
        depth = 1

class CreateMoveRegister(serializers.ModelSerializer):

    class Meta:
        model = MoveRegister
        fields = ["data", "player_move", "tile_move", "players_in_game", "play_automatic"]

    def create(self, validated_data):
        return self.__perform_creadit__(validated_data)

    def __perform_creadit__(self, validated_data, instance=None):

        data: DataGame = validated_data.get("data", None)
        if not data:
            raise("data game is requirement")
        
        player_move: Player = validated_data.get("player_move", None)
        if not player_move:
            raise("player_move is requirement")

        validated_data["game_number"] = data.match.domino_game.id
        validated_data["data_number"] = data.id
        validated_data["board_in_game"] = data.board if data.board != "" else None
        validated_data["board_left"] = data.leftValue if data.leftValue != -1 else None
        validated_data["board_right"] = data.rightValue if data.rightValue != -1 else None
        if data.match.domino_game.perPoints:
            if data.match.domino_game.inPairs:
                validated_data["score_team1"] = data.match.scoreTeam1
                validated_data["score_team2"] = data.match.scoreTeam2
            else:
                validated_data["player_points"] = getplayerpoints(data,player_move)#player_move.points
        validated_data["player_alias"] = player_move.alias
        validated_data["player_tiles"] = player_move.tiles

        return super().create(validated_data)

        