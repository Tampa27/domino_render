from rest_framework import serializers
from .models import Player
from .models import DominoGame

class PlayerSerializer(serializers.ModelSerializer):
    user = serializers.ModelField
    alias = serializers.CharField(max_length=32,required=True)
    tiles = serializers.CharField(max_length=32)
    coins = serializers.IntegerField()

    class Meta:
        model = Player
        fields = ('__all__')

    def create(self, validated_data):  
        """ 
        Create and return a new `Player` instance, given the validated data. 
        """  
        return Player.objects.create(**validated_data)  
    def update(self, instance, validated_data):  
        """ 
        Update and return an existing `Students` instance, given the validated data. 
        """  
        instance.user = validated_data.get('user', instance.user)
        instance.alias = validated_data.get('alias', instance.alias)
        instance.tiles = validated_data.get('tiles', instance.tiles)
        instance.coins = validated_data.get('coins', instance.coins)
        instance.save()
        return instance     
    
class GameSerializer(serializers.ModelSerializer):

    class Meta:
        model = DominoGame
        fields = ('__all__')

class MyPlayerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Player
        fields = ('__all__')