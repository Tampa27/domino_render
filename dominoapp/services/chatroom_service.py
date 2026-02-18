import logging
from rest_framework import status, serializers
from rest_framework.response import Response
from dominoapp.models import Player, DominoGame, ChatRoom, ChatMessage
from dominoapp.serializers import ChatMessageSerializer, ChatRoomRetrieveSerializer, ChatRoomCreateSerializer, ChatMessageCreateSerializer, ChatMessageRetrieveSerializer
from dominoapp.utils.fcm_message import FCMNOTIFICATION
from dominoapp.connectors.pusher_connector import PushNotificationConnector
logger = logging.getLogger('django')


class ChatRoomService:
    
    @staticmethod
    def process_list_message(request, chatroom_id, pagination_queryset, pagination_response):
        message_queryset_paginated = pagination_queryset(ChatMessage.objects.filter(chat_room__id = chatroom_id))
        response_data = ChatMessageSerializer(message_queryset_paginated, many = True).data
        
        response_paginated = pagination_response(data= response_data)
        
        return response_paginated
        
    @staticmethod
    def process_create(request):
        try:
            player = Player.objects.get(user__id= request.user.id)
        except:
            return Response({"status": "error", "message": "Debes autenticarte"}, status=status.HTTP_401_UNAUTHORIZED)
        
        if player.is_block:
            return Response({'status': 'error', "message":"Este player esta bloqueado, contacta con los administradores"}, status=status.HTTP_409_CONFLICT)

        data = request.data.copy()
        chatroom = None
        if "game_id" in request.data:
            try:
                game = DominoGame.objects.get(id = request.data["game_id"])
            except:
                return Response({'status': 'error', "message":"Esta mesa no existe"}, status=status.HTTP_404_NOT_FOUND)
            try:
                chatroom = ChatRoom.objects.get(in_game__id = request.data["game_id"])

                check_player = chatroom.users_list.filter(player__id = player.id).exists()
                if not check_player:
                    chatroom.users_list.add(player)
            except:
                data["in_game"] = game.id
        
        if not chatroom:            
            chat_serializer = ChatRoomCreateSerializer(data = data)
            try:
                chat_serializer.is_valid(raise_exception=True)
                chatroom: ChatRoom =  chat_serializer.save()
                players_list = Player.objects.filter(id__in = request.data["users_list"]).exclude(id=player.id)
                for player_elem in players_list:
                    chatroom.users_list.add(player_elem)
                chatroom.users_list.add(player)
                    
            except serializers.ValidationError as e:
                return Response(
                    {'status': 'error', 'message': 'Error en los datos', 'errors': e.detail},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as error:
                logger.error(f"Error al crear un chat. Error: {error}")
                return Response({'status': 'error', "message":"Algo salio mal al crear el chat, vuelve a intentar. Si continua fallando, contacta a los administradores"}, status=status.HTTP_409_CONFLICT)

        serializer = ChatRoomRetrieveSerializer(chatroom)
        return Response({'status': 'success', "data":serializer.data}, status=status.HTTP_200_OK)

    @staticmethod
    def process_create_message(request, chatroom_id):
        try:
            player = Player.objects.get(user__id= request.user.id)
        except:
            return Response({"status": "error", "message": "Debes autenticarte"}, status=status.HTTP_401_UNAUTHORIZED)
        
        if player.is_block:
            return Response({'status': 'error', "message":"Este player esta bloqueado, contacta con los administradores"}, status=status.HTTP_409_CONFLICT)

        try:
            chatroom = ChatRoom.objects.get(id = chatroom_id)
        except:
            return Response({'status': 'error', "message":"Este chat no existe"}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        if "reply_to" in request.data:
            try:
                ChatMessage.objects.get(id = request.data["reply_to"], chat_room__id = chatroom_id)
            except:
                data["reply_to"] = None
        
        data["user"] = player.id
        data["chat_room"] = chatroom.id

        print("data: ", data)
        serializer_message = ChatMessageCreateSerializer(data=data)
        try:
            serializer_message.is_valid(raise_exception=True)
            message: ChatMessage = serializer_message.save()

            response_serializer = ChatMessageRetrieveSerializer(message)
            return Response({'status': 'success', "data":response_serializer.data}, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            return Response(
                {'status': 'error', 'message': 'Error en los datos', 'errors': e.detail},
                status=400
            )
        except Exception as error:
            print("error: ", error)
            logger.error(f"Error al crear el mensaje. Error: {error}")
            return Response({'status': 'error', "message":"Algo salio mal al crear el mensaje, vuelve a intentar. Si continua fallando, contacta a los administradores"}, status=status.HTTP_409_CONFLICT)


