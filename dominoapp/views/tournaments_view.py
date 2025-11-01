from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from dominoapp.models import Tournament
from dominoapp.serializers import TournamentSerializer, TournamentCreateSerializer
from dominoapp.views.request.tournament_request import TournamentRequest
from dominoapp.services.games_service import GameService
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework.serializers import BooleanField, IntegerField, CharField

class TournamentsListPagination(PageNumberPagination):
    page_size = 3
    page_size_query_param = "page_size"

class TournamentsView(viewsets.ModelViewSet):
    queryset = Tournament.objects.filter(active=True)
    serializer_class = TournamentSerializer
    pagination_class = TournamentsListPagination
    permission_classes = [IsAuthenticated]  

    filterset_fields = ["inPairs", "variant", "status"]
    search_fields = [
        "tournament_no","deadline"
    ]

    filter_backends = [
        SearchFilter,
        OrderingFilter
    ]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]
    
    @extend_schema(
        request= {
            "application/json": TournamentCreateSerializer()
        },
        responses={
        200: TournamentSerializer()                        
        }
    )
    def create(self, request, *args, **kwargs):
        is_valid, message, status_response = TournamentRequest.validate_create(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        ######## Contruir el Creado de Torneos ############
        # return GameService.process_create(request)
        return
    ###################################