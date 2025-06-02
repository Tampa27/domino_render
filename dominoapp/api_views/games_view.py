from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from dominoapp.models import DominoGame
from dominoapp.serializers import GameSerializer, ListGameSerializer,PlayerLoginSerializer, PlayerSerializer
from dominoapp.api_views.request.games_request import GameRequest
from dominoapp.services.games_service import GameService
from drf_spectacular.utils import extend_schema, inline_serializer,OpenApiParameter, OpenApiExample
from rest_framework.serializers import BooleanField, IntegerField, CharField, ListField, UUIDField  


class GameView(viewsets.ModelViewSet):
    queryset = DominoGame.objects.all()
    serializer_class = GameSerializer
    permission_classes = [IsAuthenticated]    

    filterset_fields = ["inPairs", "perPoints", "variant", "status"]
    search_fields = [
        "player1__alias","player2__alias", "player3__alias", "player4__alias"
    ]

    filter_backends = [
        SearchFilter,
        OrderingFilter
    ]

    def create(self, request, *args, **kwargs):
        is_valid, message, status_response = GameRequest.validate_create(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_create(request)

    @extend_schema(
            responses={
            200: inline_serializer(
                name="List Games",
                fields={
                    "status": CharField(default="success"),
                    "games": ListGameSerializer(many=True),
                    "player": PlayerLoginSerializer(),
                    "game_id": IntegerField(),
                    "update": BooleanField()
                    },
            ),
            
        }
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return GameService.process_list(request, queryset)
    
    @extend_schema(
            responses={
            200: inline_serializer(
                name="Retrieve Game",
                fields={
                    "status": CharField(default="success"),
                    "game": GameSerializer(),
                    "player": PlayerSerializer(many=True)
                    },
            ),
            
        }
    )
    def retrieve(self, request, pk, *args, **kwargs):
        
        is_valid, message, status_response = GameRequest.validate_game_id(pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_retrieve(request, pk)
    
    @extend_schema(
            operation_id="games_join",
            request= None,
            responses={
            200: inline_serializer(
                name="Join Game",
                fields={
                    "status": CharField(default="success"),
                    "game": GameSerializer(),
                    "players": PlayerSerializer(many=True)
                    },
            ),
            
        }
    )
    @action(detail=True, methods=["post"])
    def join(self, request, pk):

        is_valid, message, status_response = GameRequest.validate_game_id(pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_join(request, pk)
    
    @extend_schema(
            operation_id="games_start",
            request = None,
            responses={
            200: inline_serializer(
                name="Start Game",
                fields={
                    "status": CharField(default="success"),
                    "game": GameSerializer(),
                    "players": PlayerSerializer(many=True)
                    },
            ),
            
        }
    )
    @action(detail=True, methods=["post"])
    def start(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_game_id(pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_start(pk)
    
    @action(detail=True, methods=["post"])
    def move(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_move(request, pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_move(request, pk)
    
    @action(detail=True, methods=["post"])
    def exitGame(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_game_id(pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_exitGame(request, pk)
    
    @action(detail=True, methods=["post"])
    def setWinner(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_setwinner(request, pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_setwinner(request, pk)
    
    @action(detail=True, methods=["post"])
    def setstarter(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_setstarter(request, pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_setstarter(request, pk)

    @action(detail=True, methods=["post"])
    def setwinnerstarter(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_setwinnerstarter(request, pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_setWinnerStarter(request, pk)
    
    @action(detail=True, methods=["post"])
    def setwinnerstarternext(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_setwinnerstarternext(request, pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_setWinnerStarterNext(request, pk)

    @action(detail=True, methods=["post"])
    def setpatner(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_setPatner(request, pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_setPatner(request, pk)