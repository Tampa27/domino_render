from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status 
from .models import Player
from .serializers import PlayerSerializer
from django.shortcuts import get_object_or_404 

# Create your views here.
class PlayerView(APIView):

    def get(self, request, id):
        result = Player.objects.get(id=id)
        if id:
            serializer = PlayerSerializer(result)
            return Response({"status":'success',"players":serializer.data},status=200)
        
        result = Player.objects.all()
        serializer = PlayerSerializer(result,many=True)
        return Response({"status":'success',"players":serializer.data},status=200)
    
    def get(self, request, *args, **kwargs):  
        result = Player.objects.all()  
        serializers = PlayerSerializer(result, many=True)  
        return Response({'status': 'success', "players":serializers.data}, status=200)  

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