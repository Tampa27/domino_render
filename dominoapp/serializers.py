import os
from rest_framework import serializers
from datetime import datetime
from decimal import Decimal
from dominoapp.models import Player, DominoGame, Tournament, Bank, Marketing, MoveRegister, Transaction, CurrencyRate, \
    Round, Match_Game, Pair, BankAccount
from geopy.distance import geodesic
import pytz

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
    lat = serializers.DecimalField(max_digits=9, decimal_places=7)
    lng = serializers.DecimalField(max_digits=10, decimal_places=7)
    timezone = serializers.CharField()

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
        instance.lat = validated_data.get('lat', instance.lat)
        instance.lng = validated_data.get('lng', instance.lng)
        instance.timezone = validated_data.get('timezone', instance.timezone)
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
        fields = ["id", "name", "alias", "lastTimeInSystem", "email", "photo_url", "coins", "tiles", "isPlaying", "points", "elo", "lat", "lng"]

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

class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ["id", "account_number", "phone", "created_at"]

class PlayerPaymentSerializer(serializers.ModelSerializer):
    coins = serializers.SerializerMethodField()
    account_number = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    
    def get_coins(self, obj: Player) -> int:
        return obj.earned_coins + obj.recharged_coins
    
    def get_account_number(self, obj: Player):
        transactions = Transaction.objects.filter(
            from_user__id=obj.id, type='ex', bank_account__isnull = False).order_by('-time')
        if transactions.exists():
            return transactions.first().bank_account.account_number if transactions.first().bank_account else None
        else:
            bankaccount = BankAccount.objects.filter(player__id = obj.id).order_by("-created_at")
            if bankaccount.exists():
                return bankaccount.first().account_number 
        return None
    
    def get_phone(self, obj: Player):
        bankaccount = BankAccount.objects.filter(player__id = obj.id).order_by("-created_at")
        if bankaccount.exists() and obj.phone != bankaccount.first().phone:
            return bankaccount.first().phone
        return obj.phone
    
    class Meta:
        model = Player
        fields = ["id", "name", "alias", "lastTimeInSystem", "email", "photo_url", "coins", "account_number", "phone", "lat", "lng"]

class PlayerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ["id", "name", "alias", "photo_url", "elo"]

class GameCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = DominoGame
        fields = ["variant", "maxScore", "inPairs", "perPoints", "startWinner", "lostStartInTie", "payPassValue", "payWinValue", "payMatchValue", "startAuto", "sumAllPoints", "capicua", "moveTime", "password"]

class GameSerializer(serializers.ModelSerializer):

    players_close = serializers.SerializerMethodField()
    in_tournament = serializers.SerializerMethodField()

    def get_players_close(self, obj: DominoGame) -> bool:
        # Recopilar IDs de jugadores (igual que antes)
        players_ids = []
        if obj.player1:
            players_ids.append(obj.player1.id)
        if obj.player2:
            players_ids.append(obj.player2.id)
        if obj.player3:
            players_ids.append(obj.player3.id)
        if obj.player4:
            players_ids.append(obj.player4.id)
        
        if len(players_ids) < 2:
            return False
        
        players = Player.objects.filter(
            id__in=players_ids,
            lat__isnull=False,
            lng__isnull=False
            ).only('id', 'lat', 'lng')
        players_list = list(players)
        
        for i in range(len(players_list)):
            for j in range(i + 1, len(players_list)):
                
                punto1 = (players_list[i].lat, players_list[i].lng)
                punto2 = (players_list[j].lat, players_list[j].lng)
                
                dist = geodesic(punto1, punto2).meters

                if dist < 20:  # 20 metros exactos
                    return True
        
        return False
    
    def get_in_tournament(self, obj: DominoGame) -> bool:
        return obj.in_tournament

    class Meta:
        model = DominoGame
        fields = ('__all__')

class ListGameSerializer(serializers.ModelSerializer):
    is_privated = serializers.SerializerMethodField()
    number_player = serializers.SerializerMethodField()
    players_close = serializers.SerializerMethodField()
    
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

    def get_players_close(self, obj: DominoGame) -> bool:
        # Recopilar IDs de jugadores (igual que antes)
        players_ids = []
        if obj.player1:
            players_ids.append(obj.player1.id)
        if obj.player2:
            players_ids.append(obj.player2.id)
        if obj.player3:
            players_ids.append(obj.player3.id)
        if obj.player4:
            players_ids.append(obj.player4.id)
        
        if len(players_ids) < 2:
            return False
        
        players = Player.objects.filter(
            id__in=players_ids,
            lat__isnull=False,
            lng__isnull=False
            ).only('id', 'lat', 'lng')
        players_list = list(players)
        
        for i in range(len(players_list)):
            for j in range(i + 1, len(players_list)):
                
                punto1 = (players_list[i].lat, players_list[i].lng)
                punto2 = (players_list[j].lat, players_list[j].lng)
                
                dist = geodesic(punto1, punto2).meters
                
                if dist < 20:  # 20 metros exactos
                    return True
        
        return False

    class Meta:
        model = DominoGame
        fields = ["id","table_no", "status", "variant", "start_time", "inPairs", "perPoints", "payPassValue", "payWinValue", "payMatchValue", "maxScore", "created_time", "is_privated", "password", "number_player", "players_close"]

class PairSerializaer(serializers.ModelSerializer):
    player1 = serializers.SerializerMethodField()
    player2 = serializers.SerializerMethodField()
    
    def get_player1(self, pair: Pair)-> str:
        if pair.player1:
            return pair.player1.name
        return "Desconocido"
    
    def get_player2(self, pair: Pair)-> str:
        if pair.player2:
            return pair.player2.name
        return "Desconocido"
    
    class Meta:
        model = Pair
        fields = [
            "id",
            "player1",
            "player2"
        ]

class GameMatchSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = DominoGame
        fields = ["id", "status", "table_no", "scoreTeam1", "scoreTeam2"]

class ListMatchGameSerializer(serializers.ModelSerializer):
    pair_list = PairSerializaer(many=True)
    game = GameMatchSerializer()
    
    class Meta:
        model = Match_Game
        fields = [
            "count_game",
            "pair_list",
            "games_win_team_1",
            "games_win_team_2",
            "start_at",
            "end_at",
            "game"
        ]
        depth = 1

class ListRoundSerializer(serializers.ModelSerializer):
    winner_pair_list = PairSerializaer(many=True)
    match_list = ListMatchGameSerializer(many=True, source="match_round")

    class Meta:
        model = Round
        fields = ["id","round_no", "winner_pair_list", "start_at", "end_at", "match_list"]

class TournamentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tournament
        fields = ('__all__')

class TournamentDetailsSerializer(serializers.ModelSerializer):
    
    player_list = PlayerListSerializer(many=True)
    round_list = ListRoundSerializer(many=True, source = "round_in_tournament")
    number_player = serializers.SerializerMethodField()
    first_place = serializers.SerializerMethodField()
    second_place = serializers.SerializerMethodField()
    third_place = serializers.SerializerMethodField()
    start_at = serializers.SerializerMethodField()
    end_at = serializers.SerializerMethodField()
    deadline = serializers.SerializerMethodField()
    
    def get_number_player(self, obj:Tournament)-> int:
        return obj.player_list.all().count()
        
    def get_first_place(self, tournament: Tournament)-> str:
        if tournament.place_content_type.model == "pair":
            if tournament.first_place:
                pair = tournament.first_place
                return f"{pair.player1.name} y {pair.player2.name}"
        if tournament.place_content_type.model == "player":
            if tournament.first_place:
                player = tournament.first_place
                return f"{player.name}"            
        return None
    
    def get_second_place(self, tournament: Tournament)-> str:
        if tournament.place_content_type.model == "pair":
            if tournament.second_place:
                pair = tournament.second_place
                return f"{pair.player1.name} y {pair.player2.name}"
        if tournament.place_content_type.model == "player":
            if tournament.second_place:
                player = tournament.second_place
                return f"{player.name}"            
        return None
    
    def get_third_place(self, tournament: Tournament)-> str:
        if tournament.place_content_type.model == "pair":
            if tournament.third_place:
                pair = tournament.third_place
                return f"{pair.player1.name} y {pair.player2.name}"
        if tournament.place_content_type.model == "player":
            if tournament.third_place:
                player = tournament.third_place
                return f"{player.name}"            
        return None

    def get_start_at(self, obj: Tournament):
        timezone = "America/Havana"
        if obj.start_at:
            return obj.start_at.astimezone(pytz.timezone(timezone)).strftime('%Y-%m-%dT%H:%M:%SZ')
        return None

    def get_end_at(self, obj: Tournament):
        timezone = "America/Havana"
        if obj.end_at:
            return obj.end_at.astimezone(pytz.timezone(timezone)).strftime('%Y-%m-%dT%H:%M:%SZ')
        return None
    
    def get_deadline(self, obj: Tournament):
        timezone = "America/Havana"
        if obj.deadline:
            return obj.deadline.astimezone(pytz.timezone(timezone)).strftime('%Y-%m-%dT%H:%M:%SZ')
        return None
    
    class Meta:
        model = Tournament
        exclude = [
            "notification_1",
            "notification_30",
            "notification_5",
            "place_content_type",
            "first_place_object_id",
            "second_place_object_id",
            "third_place_object_id",
        ]

class TournamentListSerializer(serializers.ModelSerializer):

    number_player = serializers.SerializerMethodField()
    start_at = serializers.SerializerMethodField()
    deadline = serializers.SerializerMethodField()
    
    def get_number_player(self, obj:Tournament):
        return obj.player_list.all().count()
    
    def get_start_at(self, obj: Tournament):
        timezone = "America/Havana"
        if obj.start_at:
            return obj.start_at.astimezone(pytz.timezone(timezone)).strftime('%Y-%m-%dT%H:%M:%SZ')
        return None
    
    def get_deadline(self, obj: Tournament):
        timezone = "America/Havana"
        if obj.deadline:
            return obj.deadline.astimezone(pytz.timezone(timezone)).strftime('%Y-%m-%dT%H:%M:%SZ')
        return None

    class Meta:
        model = Tournament
        fields = [
            "id",
            "name",
            "winner_payout",
            "second_payout",
            "third_payout",
            "registration_fee",
            "deadline",
            "start_at",
            "status",
            "tournament_no",
            "variant",
            "maxScore",
            "inPairs",
            "min_player",
            "max_player",
            "number_match_win",
            "number_player"
        ]

class TournamentCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tournament
        fields = ["name", "variant", "maxScore", "inPairs", "startWinner",  "moveTime", "min_player", "max_player", "active", "registration_fee", "deadline", "start_at", "winner_payout", "second_payout", "third_payout", "number_match_win"]

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
    user = serializers.SerializerMethodField()
    coins = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    admin = PlayerListSerializer()
    
    def get_status(self, obj: Transaction) -> str:
        return obj.get_status
    
    def get_user(self, obj: Transaction) -> dict:
        if obj.from_user is not None:
            serializers = PlayerListSerializer(obj.from_user)
            return serializers.data
        elif obj.to_user is not None:
            serializers = PlayerListSerializer(obj.to_user)
            return serializers.data
        return None
    
    def get_coins(self, obj: Transaction) -> int:
        recharged_coins = int(obj.amount)
        paymentmethod = obj.paymentmethod if obj.paymentmethod is not None else 'transferencia' 
        currency_rate = CurrencyRate.objects.filter(code=paymentmethod)
        if currency_rate:
            recharged_coins = int(recharged_coins*currency_rate.first().rate_exchange)
        return recharged_coins
    
    def get_time(self, obj: Transaction):
        timezone = "America/Havana"
        if obj.from_user:
            timezone = obj.from_user.timezone
        elif obj.to_user:
            timezone = obj.to_user.timezone
        return obj.time.astimezone(pytz.timezone(timezone))
    
    class Meta:
        model = Transaction
        fields = ['id', 'user', 'amount', 'coins','type', 'status', 'time', 'descriptions', 'admin', 'paymentmethod', 'whatsapp_url']

class ListTransactionsAdminSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    coins = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    admin = PlayerListSerializer()
    account_number = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    
    def get_status(self, obj: Transaction) -> str:
        return obj.get_status
    
    def get_user(self, obj: Transaction) -> dict:
        if obj.from_user is not None:
            serializers = PlayerPaymentSerializer(obj.from_user)
            return serializers.data
        elif obj.to_user is not None:
            serializers = PlayerPaymentSerializer(obj.to_user)
            return serializers.data
        return None
    
    def get_coins(self, obj: Transaction) -> int:
        recharged_coins = int(obj.amount)
        paymentmethod = obj.paymentmethod if obj.paymentmethod is not None else 'transferencia' 
        currency_rate = CurrencyRate.objects.filter(code=paymentmethod)
        if currency_rate:
            recharged_coins = int(recharged_coins*currency_rate.first().rate_exchange)
        return recharged_coins
    
    def get_time(self, obj: Transaction):
        timezone = "America/Havana"
        return obj.time.astimezone(pytz.timezone(timezone)).strftime('%Y-%m-%dT%H:%M:%S.%f')
    
    def get_account_number(self, obj: Transaction):
        if obj.bank_account:
            return obj.bank_account.account_number
        return None
    
    def get_phone(self, obj: Transaction):
        if obj.bank_account:
            return obj.bank_account.phone
        elif obj.from_user:
            return obj.from_user.phone
        elif obj.to_user:
            return obj.to_user.phone
        return None
    
    class Meta:
        model = Transaction
        fields = ['id', 'user', 'amount', 'coins','type', 'status', 'time', 'descriptions', 'admin', 'paymentmethod', 'account_number', 'phone', 'whatsapp_url']