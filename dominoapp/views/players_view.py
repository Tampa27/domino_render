from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
from dominoapp.models import Player, BlockPlayer
from dominoapp.serializers import PlayerSerializer, PlayerLoginSerializer, \
    PlayerNotificationSerializer, PlayerRetrieveSerializer, PlayerConfigSerializer, \
    PlayerListSerializer, PlayerPersonalRankinSerializer
from dominoapp.services.player_service import PlayerService, PlayerRankinSerializer
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
        elif self.action in ["send_notification"]:
            permission_classes = [IsAdminUser]
        else:  
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        if self.action in ["list_player_invitations"]:
            player_bloqued = BlockPlayer.objects.all().values_list("player_blocked__id", flat=True)
            queryset = Player.objects.filter(send_invitation_notifications=True).exclude(user__id = self.request.user.id).exclude(id__in=player_bloqued)
        else:
            queryset = Player.objects.all()
        return queryset 
    
    def get_serializer_class(self):
        if self.action in ["list_player_invitations"]:
            serializer_class = PlayerListSerializer
        else:
            serializer_class = PlayerSerializer
        return serializer_class

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
            responses={
            200: PlayerListSerializer(many=True)
        }
    )
    @action(detail=False, methods=["get"], url_path="players_invitations")
    def list_player_invitations(self, request, *args, **kwargs):
        response = super().list(request,*args, **kwargs)
        return Response(response.data, status=status.HTTP_200_OK)
    
    @extend_schema(
            operation_id="players_rankin",
            parameters=[
                OpenApiParameter(name="page", type=int),
                OpenApiParameter(name="page_size", type=int,),
                OpenApiParameter(name="ordering", type=str, enum=[
                    'elo', '-elo', 
                    'data_percent', '-data_percent', 
                    'match_percent', '-match_percent',
                    'coins', '-coins',
                    'data_wins', '-data_wins',
                    'match_wins', '-match_wins',
                    'balance_coins', '-balance_coins',
                    'pass_player', '-pass_player'
                    ]),
                OpenApiParameter(name="start_date", type=str, description="Fecha de inicio con formato `d-m-y`"),
                OpenApiParameter(name="end_date", type=str, description="Fecha final con formato `d-m-y`"),
                OpenApiParameter(name="search", type=str, description="A search term.")
                ],
            request=None,
            responses={
            status.HTTP_200_OK:inline_serializer(
                name="player_ranking",
                fields={
                    "count": IntegerField(),
                    "next": URLField(),
                    "previous": URLField(),
                    "results": PlayerRankinSerializer(many=True)
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
        
        queryset = self.filter_queryset(self.get_queryset())
        return PlayerService.process_rankin(request, queryset)
    
    @extend_schema(
            operation_id="personal_rankin",
            parameters=[
                OpenApiParameter(name="start_date", type=str, description="Fecha de inicio con formato `d-m-y`"),
                OpenApiParameter(name="end_date", type=str, description="Fecha final con formato `d-m-y`")
                ],
            request=None,
            responses={
                status.HTTP_200_OK:PlayerPersonalRankinSerializer()
            }
    )
    @action(detail=False, methods=["get"])
    def personal_rankin(self, request, *args, **kwargs):
        is_valid, message, status_response = PlayerRequest.validate_personal_rankin(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PlayerService.process_personal_rankin(request)
    
    @extend_schema(
            responses={
            200: inline_serializer(
                name="Retrieve Player",
                fields={
                    "status": CharField(default="success"),
                    "player": PlayerRetrieveSerializer(),
                    "game_id": IntegerField()
                    },
            ),
            
        }
    )
    def retrieve(self, request, pk):
        return PlayerService.process_retrieve(request)
    
    @extend_schema(
            responses={
            200: PlayerConfigSerializer()
            },
    )
    @action(detail=False, methods=["get"], url_path="config")
    def config(self, request, pk):        
        return PlayerService.process_conf(request)
    
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

        is_valid, message, status_response = PlayerRequest.validate_update(request, is_partial)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PlayerService.process_update(request, is_partial)

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
                "application/json": inline_serializer(
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
            operation_id="list_notification",
            methods=["get"],
            request=None,
            responses={
                status.HTTP_200_OK:inline_serializer(
                name="player_notifications",
                fields={
                    "count": IntegerField(),
                    "next": URLField(),
                    "previous": URLField(),
                    "results": PlayerNotificationSerializer(many=True)
                }
            )
            }
            )    
    @extend_schema(
            operation_id="send_notifications",
            methods=["post"],
            request={
                "application/json": inline_serializer(
                name="Send Notification Request",
                fields={
                    "player_id": IntegerField(required=False),
                    "title": CharField(required=True),
                    "text": CharField(required=True)                    
                    },
            ),    
            },
            responses={
            204: None
            
        }
    ) 
    @action(detail=False, methods=["post", "get"], url_path="notification")
    def send_list_notification(self, request):

        if self.request.method == "POST":       
            is_valid, message, status_response = PlayerRequest.validate_send_notification(request)
            
            if not is_valid:
                return Response(data ={
                    "status":'error',
                    "message": message
                }, status = status_response)

            return PlayerService.process_send_notification(request)
        elif self.request.method == "GET":
            is_valid, message, status_response = PlayerRequest.validate_list_notifications(request)
        
            if not is_valid:
                return Response(data ={
                    "status":'error',
                    "message": message
                }, status = status_response)
            
            return PlayerService.process_list_notification(request)
        else:
            return Response(data ={
                    "status":'error',
                    "message": "Method not allowed"
                }, status = status.HTTP_405_METHOD_NOT_ALLOWED)
        
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
    
