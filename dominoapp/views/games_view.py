from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from dominoapp.models import DominoGame
from dominoapp.serializers import GameSerializer, GameCreateSerializer, ListGameSerializer,PlayerLoginSerializer, PlayerGameSerializer
from dominoapp.views.request.games_request import GameRequest
from dominoapp.services.games_service import GameService
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework.serializers import BooleanField, IntegerField, CharField


class GameView(viewsets.ModelViewSet):
    queryset = DominoGame.objects.all()
    serializer_class = GameSerializer
    permission_classes = [IsAuthenticated]    

    filterset_fields = ["inPairs", "perPoints", "variant", "status"]
    search_fields = [
        "player1__alias","player2__alias", "player3__alias", "player4__alias", "table_no"
    ]

    filter_backends = [
        SearchFilter,
        OrderingFilter
    ]
    
    def get_queryset(self):
        if self.action in ["list", "join", "start", "exitGame"]:
            queryset = DominoGame.objects.filter(tournament__isnull=True)
        else:
            queryset = DominoGame.objects.all()
        return queryset

    @extend_schema(
            request= {
                200:GameCreateSerializer()
            },
            responses={
            200: inline_serializer(
                name="Create Game",
                fields={
                     "status": CharField(default="success"),
                    "game": GameSerializer()
                }
            )            
        }
    )
    def create(self, request, *args, **kwargs):
        is_valid, message, status_response = GameRequest.validate_create(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_create(request)

    @extend_schema(
            parameters=[
                OpenApiParameter("app_version",description="Field to confirm the currently used application version.")
            ],
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
        is_valid, message, status_response = GameRequest.validate_list(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        queryset = self.filter_queryset(self.get_queryset())
        return GameService.process_list(request, queryset)
    
    @extend_schema(
            responses={
            200: inline_serializer(
                name="Retrieve Game",
                fields={
                    "status": CharField(default="success"),
                    "game": GameSerializer(),
                    "players": PlayerGameSerializer(many=True)
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
                    "players": PlayerGameSerializer(many=True)
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
                    "players": PlayerGameSerializer(many=True)
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
    
    @extend_schema(
            operation_id="game_move",
            request = {
                200:inline_serializer(
                    name="Move Tile Request",
                    fields={
                        "tile": CharField(required = True),
                        },
                )
            },
            responses={
            200: inline_serializer(
                name="Move Tile Response",
                fields={
                    "status": CharField(default="success"),
                    },
            ),
            
        }
    )
    @action(detail=True, methods=["post"])
    def move(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_move(request, pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_move(request, pk)
    
    @extend_schema(
            operation_id="game_exit",
            request = None,
            responses={
            200: inline_serializer(
                name="Exit Game Response",
                fields={
                    "status": CharField(default="success"),
                    },
            ),
            
        }
    )
    @action(detail=True, methods=["post"], url_path="exit")
    def exitGame(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_game_id(pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_exitGame(request, pk)
    
    @extend_schema(
            operation_id="games_set_winner",
            request = {
                "application/json": inline_serializer(
                    name="Set Winner Game Request",
                    fields={
                        "winner": IntegerField()
                    }
                )
            },
            responses={
            200: inline_serializer(
                name="Set Winner Game Response",
                fields={
                    "status": CharField(default="success"),
                    },
            ),
            
        }
    )
    @action(detail=True, methods=["post"])
    def set_winner(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_setwinner(request, pk)
        
        ## Esta Bloqueada por el momento para que no se tarequee en los juegos por pareja
        is_valid = False
        message = "Esta Bloqueada por el momento para evitar conflictos en los juegos por pareja."
        status_response = 400
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_setwinner(request, pk)
    
    @extend_schema(
            operation_id="games_set_starter",
            request = {
                "application/json": inline_serializer(
                    name="Set Starter Game Request",
                    fields={
                        "starter": IntegerField()
                    }
                )
            },
            responses={
            200: inline_serializer(
                name="Set Starter Game Response",
                fields={
                    "status": CharField(default="success"),
                    },
            ),
            
        }
    )
    @action(detail=True, methods=["post"])
    def set_starter(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_setstarter(request, pk)
        
        ## Esta Bloqueada por el momento para que no se tarequee en los juegos por pareja
        is_valid = False
        message = "Esta Bloqueada por el momento para evitar conflictos en los juegos por pareja."
        status_response = 400
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_setstarter(request, pk)

    @extend_schema(
            operation_id="games_set_winner_starter",
            request = {
                "application/json": inline_serializer(
                    name="Set Winner Starter Game Request",
                    fields={
                        "winner" : IntegerField(required=True),
                        "starter": IntegerField(required=True)
                    }
                )
            },
            responses={
            200: inline_serializer(
                name="Set Winner Starter Game Response",
                fields={
                    "status": CharField(default="success"),
                    },
            ),
            
        }
    )
    @action(detail=True, methods=["post"])
    def set_winner_starter(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_setwinnerstarter(request, pk)
        
        ## Esta Bloqueada por el momento para que no se tarequee en los juegos por pareja
        is_valid = False
        message = "Esta Bloqueada por el momento para evitar conflictos en los juegos por pareja."
        status_response = 400
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_setWinnerStarter(request, pk)
    
    @extend_schema(
            operation_id="games_set_winner_starter_next",
            request = {
                "application/json": inline_serializer(
                    name="Set Winner, Starter and Next Game Request",
                    fields={
                        "winner" : IntegerField(required=True),
                        "starter": IntegerField(required=True),
                        "next_player": IntegerField(required=True)
                    }
                )
            },
            responses={
            200: inline_serializer(
                name="Set Winner, Starter and Next Game Response",
                fields={
                    "status": CharField(default="success"),
                    },
            ),
            
        }
    )
    @action(detail=True, methods=["post"])
    def set_winner_starter_next(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_setwinnerstarternext(request, pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_setWinnerStarterNext(request, pk)

    @extend_schema(
            operation_id="games_set_patner",
            request = {
                200: inline_serializer(
                    name="Set Patner Game Request",
                    fields={
                        "alias" : CharField(required=True)
                    }
                )
            },
            responses={
            200: inline_serializer(
                name="Set Patner Game Response",
                fields={
                    "status": CharField(default="success"),
                    },
            ),
            404: inline_serializer(
                name="Set Patner Response Error",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            
        }
    )
    @action(detail=True, methods=["post"])
    def set_patner(self, request, pk):
        is_valid, message, status_response = GameRequest.validate_setPatner(request, pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return GameService.process_setPatner(request, pk)