import os
from rest_framework import serializers
from decimal import Decimal
from dominoapp.models import Player, DominoGame, Tournament, Bank, Marketing, MoveRegister, Transaction

class PlayerSerializer(serializers.ModelSerializer):
    alias = serializers.CharField(max_length=32,required=True)
    tiles = serializers.CharField(max_length=32)
    earned_coins = serializers.IntegerField()
    recharged_coins = serializers.IntegerField()
    points = serializers.IntegerField()
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
        instance.points = validated_data.get('points', instance.points)
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

class PlayerRankinSerializer(serializers.ModelSerializer):
    coins = serializers.SerializerMethodField()
    data_win_percent = serializers.SerializerMethodField()
    match_win_percent = serializers.SerializerMethodField()
    
    def get_coins(self, obj: Player) -> int:
        return obj.earned_coins + obj.recharged_coins
    
    def get_data_win_percent(self, obj: Player) -> str:
        total_game = obj.dataWins + obj.dataLoss
        if total_game == 0:
            return "0.00"
        else:
           win_percent = Decimal((obj.dataWins * 100)/total_game)
           return str(round(win_percent, 2))
    
    def get_match_win_percent(self, obj: Player) -> str:
        total_game = obj.matchWins + obj.matchLoss
        if total_game == 0:
            return "0.00"
        else:
           win_percent = Decimal((obj.matchWins * 100)/total_game)
           return str(round(win_percent, 2))
    
    class Meta:
        model = Player
        fields = ["id", "name", "alias", "photo_url", "coins", "earned_coins", "recharged_coins", "elo", "dataWins", "dataLoss", "data_win_percent", "matchWins", "matchLoss", "match_win_percent"]

class PlayerGameSerializer(serializers.ModelSerializer):
    coins = serializers.SerializerMethodField()
    def get_coins(self, obj: Player) -> int:
        return obj.earned_coins + obj.recharged_coins
    
    class Meta:
        model = Player
        fields = ["id", "name", "alias", "lastTimeInSystem", "email", "photo_url", "coins", "tiles", "isPlaying", "points", "elo"]

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
        fields = ["id", "name", "alias", "lastTimeInSystem", "email", "photo_url", "coins", "earned_coins", "recharged_coins", "referral_code", "url", "lat", "lng"]

class GameCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = DominoGame
        fields = ["variant", "maxScore", "inPairs", "perPoints", "startWinner", "lostStartInTie", "payPassValue", "payWinValue", "payMatchValue", "startAuto", "sumAllPoints", "capicua", "moveTime", "password"]


class GameSerializer(serializers.ModelSerializer):

    class Meta:
        model = DominoGame
        fields = ('__all__')

class ListGameSerializer(serializers.ModelSerializer):
    is_privated = serializers.SerializerMethodField()
    number_player = serializers.SerializerMethodField()

    def get_is_privated(self, obj: DominoGame)-> bool:
        return True if obj.password != "" else False
    
    def get_number_player(self, obj: DominoGame) -> int:
        total_player = 0
        if obj.player1:
            total_player += 1
        if obj.player2:
            total_player += 1
        if obj.player3:
            total_player += 1
        if obj.player4:
            total_player += 1
        return total_player

    class Meta:
        model = DominoGame
        fields = ["id","table_no", "status", "variant", "start_time", "inPairs", "perPoints", "payPassValue", "payWinValue", "payMatchValue", "maxScore", "created_time", "is_privated", "password", "number_player"]

class TournamentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tournament
        fields = ('__all__')

class TournamentCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tournament
        fields = ["variant", "maxScore", "inPairs", "startWinner",  "moveTime", "min_player", "active", "registration_fee", "deadline", "start_at", "winner_payout", "second_payout", "third_payout"]

class MyPlayerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Player
        fields = ('__all__')

class BankSerializer(serializers.ModelSerializer):

    class Meta:
        model = Bank
        fields = ('__all__')

class MarketingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marketing
        fields = ["image", "text", "url"]
        depth = 1

class CreateMoveRegister(serializers.ModelSerializer):

    class Meta:
        model = MoveRegister
        fields = ["game", "player_move", "tile_move", "players_in_game", "play_automatic"]

    def create(self, validated_data):
        return self.__perform_creadit__(validated_data)

    def __perform_creadit__(self, validated_data, instance=None):

        game: DominoGame = validated_data.get("game", None)
        if not game:
            raise("game is requirement")
        player_move: Player = validated_data.get("player_move", None)
        if not player_move:
            raise("player_move is requirement")

        validated_data["game_number"] = game.id
        validated_data["board_in_game"] = game.board if game.board != "" else None
        validated_data["board_left"] = game.leftValue if game.leftValue != -1 else None
        validated_data["board_right"] = game.rightValue if game.rightValue != -1 else None
        if game.perPoints:
            if game.inPairs:
                validated_data["score_team1"] = game.scoreTeam1
                validated_data["score_team2"] = game.scoreTeam2
            else:
                validated_data["player_points"] = player_move.points
        validated_data["player_alias"] = player_move.alias
        validated_data["player_tiles"] = player_move.tiles

        return super().create(validated_data)

class ListTransactionsSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    from_user = PlayerLoginSerializer()
    to_user = PlayerLoginSerializer()
    admin = PlayerLoginSerializer()
    
    def get_status(self, obj: Transaction) -> str:
        return obj.get_status
    
    class Meta:
        model = Transaction
        fields = ['id', 'from_user', 'to_user', 'amount', 'type', 'status', 'time', 'descriptions', 'admin', 'paymentmethod', 'whatsapp_url']