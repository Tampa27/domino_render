import shortuuid
import os
import logging
from rest_framework import status
from rest_framework.response import Response
from django.db.models import Q, Sum, OuterRef, Subquery
from django.http import HttpResponse
from django.shortcuts import redirect
from datetime import datetime, timedelta
from dominoapp.models import Player, ChatRoom, ChatMessage
from dominoapp.serializers import ChatMessageSerializer
from dominoapp.utils.constants import ApiConstants
from dominoapp.utils.fcm_message import FCMNOTIFICATION
from dominoapp.connectors.discord_connector import DiscordConnector
from dominoapp.connectors.pusher_connector import PushNotificationConnector
logger = logging.getLogger('django')


class ChatRoomService:
    
    @staticmethod
    def process_list_message(request, chatroom_id, pagination_queryset, pagination_response):
        message_queryset_paginated = pagination_queryset(ChatMessage.objects.filter(chat_room__id = chatroom_id))
        response_data = ChatMessageSerializer(message_queryset_paginated, many = True).data
        print("response_data: ", response_data)
        response_paginated = pagination_response(data= response_data)
        
        return response_paginated
        