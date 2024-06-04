from rest_framework import serializers
from .models import Player

class PlayerSerializer(serializers.ModelSerializer):
    user = serializers.ModelField
    alias = serializers.CharField(max_length=32,required=True)

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
        instance.save()
        return instance     