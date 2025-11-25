from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
from dominoapp.models import Player
from dominoapp.serializers import PlayerSerializer, PlayerLoginSerializer
from dominoapp.services.player_service import PlayerService
from dominoapp.views.request.players_request import PlayerRequest
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework.serializers import IntegerField, CharField, URLField


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
        if self.action in ["login","refer_register"]:
            permission_classes = [AllowAny]
        else:  
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @extend_schema(
            responses={
            200: inline_serializer(
                name="List Player",
                fields={
                    "status": CharField(default="success"),
                    "player": PlayerSerializer(many=True)
                    },
            ),
            
        }
    )
    def list(self, request, *args, **kwargs):
        response = super().list(request,*args, **kwargs)
        return Response({"status":'success',"player":response.data},status=status.HTTP_200_OK)
    
    @extend_schema(
            operation_id="players_rankin",
            parameters=[
                OpenApiParameter(name="page", type=int),
                OpenApiParameter(name="page_size", type=int,),
                OpenApiParameter(name="ordering", type=str, enum=[
                    'elo', '-elo', 
                    'data_percent', '-data_percent', 
                    'match_percent', '-match_percent',
                    'total_coins', '-total_coins'
                    ])
                ],
            request=None,
            responses={
            status.HTTP_200_OK:inline_serializer(
                name="player_ranking",
                fields={
                    "count": IntegerField(),
                    "next": URLField(),
                    "previous": URLField(),
                    "results": PlayerSerializer(many=True)
                }
            )
        }
    )
    @action(detail=False, methods=["get"])
    def rankin(self, request, *args, **kwargs):
        is_valid, message, status_response = PlayerRequest.validate_rankin(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)

        return PlayerService.process_rankin(request)
    
    @extend_schema(
            responses={
            200: inline_serializer(
                name="Retrieve Player",
                fields={
                    "status": CharField(default="success"),
                    "player": PlayerSerializer(),
                    "game_id": IntegerField()
                    },
            ),
            
        }
    )
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

    @extend_schema(
            operation_id="players_login",
            request={
                200: inline_serializer(
                name="Login Player Request",
                fields={
                    "token": CharField(),
                    "refer_code": CharField(max_length=6, min_length=6, required=False),
                    "fcm_token": CharField(required=False)
                    },
            ),    
            },
            responses={
            200: inline_serializer(
                name="Login Player Response",
                fields={
                    "refresh": CharField(),
                    "access": CharField(),
                    "user": PlayerLoginSerializer()
                    },
            ),
            
        }
    ) 
    @action(detail=False, methods=["post"])
    def login(self, request):
               
        is_valid, message, status_response = PlayerRequest.validate_login(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)

        return PlayerService.process_login(request)
    
    @extend_schema(
            operation_id="fcm_register",
            request={
                204: inline_serializer(
                name="FCM Register Request",
                fields={
                    "fcm_token": CharField(required=False)
                    },
            ),    
            },
            responses={
            204: None
            
        }
    ) 
    @action(detail=False, methods=["post"])
    def fcm_register(self, request):
               
        is_valid, message, status_response = PlayerRequest.validate_fcm_register(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)

        return PlayerService.process_fcm_register(request)
    
    @extend_schema(
            operation_id="players_refer_code",
            request=None,
            responses={
            200: inline_serializer(
                name="Refer Code Response",
                fields={
                    "refer_code": CharField(max_length = 6, min_length = 6),
                    },
            ),
            
        }
    ) 
    @action(detail=False, methods=["get"])
    def refer_code(self, request):
        return PlayerService.process_refer_code(request)
    
    @extend_schema(
            operation_id="players_refer_register",
            parameters=[
                OpenApiParameter(
                    name="refer_code",
                    type=str,)
                ],
            request=None,
            responses={
            status.HTTP_308_PERMANENT_REDIRECT: None            
        }
    ) 
    @action(detail=False, methods=["get"], url_path="refer")
    def refer_register(self, request):
        return PlayerService.process_refer_register(request)