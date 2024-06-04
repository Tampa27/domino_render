from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status 
from .models import Player
from .serializers import PlayerSerializer

# Create your views here.
class PlayerView(APIView):

    def get(self, request, *args, **kwargs):
        result = Player.objects.all()
        serializer = PlayerSerializer(result,many=True)
        return Response({"status":'success',"players":serializer.data},status=200)