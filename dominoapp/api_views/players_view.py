from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
from dominoapp.models import Player
from dominoapp.serializers import PlayerSerializer
from dominoapp.services.player_service import PlayerService
from dominoapp.api_views.request.players_request import PlayerRequest


class PlayerView(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = PlayerSerializer

    filterset_fields = ["name", "alias", "email"]
    search_fields = [
        "name","email", "alias"
    ]

    filter_backends = [
        SearchFilter,
        OrderingFilter
    ]
    
    def get_permissions(self):
        if self.action in ["login"]:
            permission_classes = [AllowAny]
        else:  
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        response = super().list(request,*args, **kwargs)
        return Response({"status":'success',"player":response.data},status=status.HTTP_200_OK)
    
    def retrieve(self, request, pk):
        is_valid, message, status_response = PlayerRequest.validate_retrieve(pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PlayerService.process_retrieve(request, pk)
    
    def create(self, request):        
        is_valid, message, status_response = PlayerRequest.validate_create(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)

        return PlayerService.process_create(request)
        
    def update(self, request, pk, *args, **kwargs):  
        is_partial = kwargs.pop('partial', False)

        is_valid, message, status_response = PlayerRequest.validate_update(request, pk, is_partial)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PlayerService.process_update(request, pk, is_partial)

    def destroy(self, request, pk):
        is_valid, message, status_response = PlayerRequest.validate_retrieve(pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PlayerService.process_delete(request, pk)  
        
    @action(detail=False, methods=["post"])
    def login(self, request):
               
        is_valid, message, status_response = PlayerRequest.validate_login(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)

        return PlayerService.process_login(request)