from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import OrderingFilter, SearchFilter
from django.db.models import Q
from dominoapp.models import ChatRoom
from dominoapp.views.request.chatroom_request import ChatRoomRequest
from dominoapp.views.filters.payment_filter import PaymentSearchFilter
from dominoapp.services.chatroom_service import ChatRoomService
from dominoapp.serializers import ChatRoomSerializer, ChatRoomRetrieveSerializer
from dominoapp.utils.request_permitions import IsSuperAdminUser
from drf_spectacular.utils import extend_schema, inline_serializer,OpenApiParameter, OpenApiExample
from rest_framework.serializers import BooleanField, IntegerField, CharField, ListField, UUIDField 


class ChatRoomListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    
class ChatRoomView(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = ChatRoomListPagination
    serializer_class = ChatRoomSerializer
    filter_backends = [
        OrderingFilter,
        SearchFilter
        ]
    search_fields = []
    
    def get_serializer_class(self):
        if self.action in ["retrieve"]:
            serializer_class = ChatRoomRetrieveSerializer
        else:
            serializer_class = ChatRoomSerializer
        return serializer_class

    @extend_schema(
        operation_id="chatroom_list_message",
        parameters=[
            OpenApiParameter(name="ordering", description="Which field to use when ordering the results."),
            OpenApiParameter(name="page", type=int, description="A page number within the paginated result set."),
            OpenApiParameter(name="page_size", type=int, description= "Number of results to return per page."),
            OpenApiParameter(name="search", description="A search term.")
        ]
    )
    @action(methods=["GET"], detail=True)
    def list_message(self, request, pk):
        is_valid, message, status_response = ChatRoomRequest.validate_uuid(request, pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return ChatRoomService.process_list_message(request, pk, self.paginate_queryset, self.get_paginated_response)
    