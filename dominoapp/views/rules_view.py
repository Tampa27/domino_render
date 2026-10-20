from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from dominoapp.models import RulesGame
from dominoapp.serializers import Create_Rules_Serializer, List_Rules_Game_Serializer,PlayerOnListGameSerializer, PlayerGameSerializer, GameSerializer
from dominoapp.views.request.games_request import GameRequest
from dominoapp.services.rule_service import RuleService
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework.serializers import BooleanField, IntegerField, CharField


class RuleView(viewsets.ModelViewSet):
    queryset = RulesGame.objects.all()
    serializer_class = Create_Rules_Serializer
    permission_classes = [IsAuthenticated]    

    filterset_fields = ["inPairs", "perPoints", "variant", "status"]
    search_fields = []

    filter_backends = [
        SearchFilter,
        OrderingFilter
    ]
 
    @extend_schema(
            parameters=[
                OpenApiParameter("app_version",description="Field to confirm the currently used application version.")
            ],
            responses={
            200: inline_serializer(
                name="List Rules",
                fields={
                    "status": CharField(default="success"),
                    "rules": List_Rules_Game_Serializer(many=True),
                    "player": PlayerOnListGameSerializer(),
                    "game_id": IntegerField(),
                    "update": BooleanField()
                    }
            )
            
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
        return RuleService.process_list(request, queryset)

     
    @extend_schema(
            operation_id="rule_join",
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
        
        return RuleService.process_join(request, pk)
    