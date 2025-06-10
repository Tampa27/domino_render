from rest_framework import serializers
from .models import Player
from .models import DominoGame
from .models import Bank, Marketing

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

class PlayerLoginSerializer(serializers.ModelSerializer):
    coins = serializers.SerializerMethodField()
    def get_coins(self, obj: Player) -> int:
        return obj.earned_coins + obj.recharged_coins
    
    class Meta:
        model = Player
        fields = ["id", "name", "alias", "lastTimeInSystem", "email", "photo_url", "coins", "earned_coins", "recharged_coins"]

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
        fields = ["id", "status", "variant", "start_time", "inPairs", "perPoints", "payPassValue", "payWinValue", "payMatchValue", "maxScore", "created_time", "is_privated", "password", "number_player"]


class MyPlayerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Player
        fields = ('__all__')

class BankSerializer(serializers.ModelSerializer):

    class Meta:
        model = Bank
        fields = ('__all__')

class MarketingSerializer(serializers.ModelSerializer):
    user = PlayerLoginSerializer()
    class Meta:
        model = Marketing
        fields = ["user", "image", "text", "url", "created_at", "updated_at"]
        depth = 1