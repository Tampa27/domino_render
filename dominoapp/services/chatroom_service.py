import logging
import pytz
from rest_framework import status, serializers
from rest_framework.response import Response
from django.db import transaction
from dominoapp.models import Player, DominoGame, ChatRoom, ChatMessage
from dominoapp.serializers import ChatMessageSerializer, ChatRoomRetrieveSerializer, ChatRoomCreateSerializer, ChatMessageCreateSerializer, ChatMessageRetrieveSerializer
from dominoapp.utils.websocket_utils import send_ws_chat_message, get_count_and_up_chat_key, get_count_chat_key
from dominoapp.utils.constants import WSActions
logger = logging.getLogger('django')


class ChatRoomService:
    
    @staticmethod
    def process_list_message(request, chatroom_id, pagination_queryset, pagination_response):
        try:
            player = Player.objects.get(user__id = request.user.id)
        except:
            player = None
        
        message_queryset_paginated = pagination_queryset(ChatMessage.objects.filter(chat_room__id = chatroom_id))
        messages_serializer = ChatMessageSerializer(message_queryset_paginated, many = True)
        messages_serializer.context['player_request'] = player
        response_data = messages_serializer.data
        
        response_paginated = pagination_response(data= response_data)
        response_paginated.data["c_chat"] = get_count_chat_key(chatroom_id)
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
        serializer.context['player_request'] = player
        return Response({'status': 'success', "data":serializer.data}, status=status.HTTP_200_OK)

    @staticmethod
    def perfom_send_message(player: Player, chatroom_id, data):
        if player.is_block:
            return 'error', "Este player esta bloqueado, contacta con los administradores", status.HTTP_409_CONFLICT

        try:
            chatroom = ChatRoom.objects.get(id = chatroom_id)
        except:
            return 'error', "Este chat no existe", status.HTTP_409_CONFLICT

        check_player = chatroom.users_list.filter(player__id = player.id).exists()
        if not check_player:
            return 'error', "No tienes permitido escribir en este chat", status.HTTP_409_CONFLICT

        if "reply_to" in data:
            try:
                ChatMessage.objects.get(id = data["reply_to"], chat_room__id = chatroom_id)
            except:
                data["reply_to"] = None
        
        data["user"] = player.id
        data["chat_room"] = chatroom.id

        serializer_message = ChatMessageCreateSerializer(data=data)
        try:
            serializer_message.is_valid(raise_exception=True)
            message: ChatMessage = serializer_message.save()

            response_serializer = ChatMessageRetrieveSerializer(message)
            response_serializer.context['player_request'] = player
            
            ws_data = {                
                "p": player.id,
                "mg": message.message,                
                "time": message.created_at.astimezone(pytz.timezone(player.timezone)).strftime('%d-%m-%Y, %H:%M:%S')
            }
            if "reply_to" in data and data["reply_to"]:
                ws_data["rtmg"] = data["reply_to"]

            # Registramos la función para que corra SOLO si el commit es exitoso
            try:
                count_key = get_count_and_up_chat_key(chatroom_id)
                transaction.on_commit(lambda ck=count_key: send_ws_chat_message(
                    chat_id= chatroom_id,
                    payload={
                        "a": WSActions.NEW_MESSAGE,
                        "c_chat": ck,
                        "d": ws_data
                    }
                ))
            except Exception as error:
                logger.error(f"Error al enviar el WS en el perfom_send_message: {error}")

            return response_serializer.data, None, None
        except serializers.ValidationError as e:
            return 'error', f'Error en los datos, errors: {e.detail}', status.HTTP_400_BAD_REQUEST
            
        except Exception as error:
            logger.error(f"Error al crear el mensaje. Error: {error}")
            return 'error', "Algo salio mal al crear el mensaje, vuelve a intentar. Si continua fallando, contacta a los administradores", status.HTTP_409_CONFLICT

    @staticmethod
    def process_create_message(request, chatroom_id):
        try:
            player = Player.objects.get(user__id= request.user.id)
        except:
            return Response({"status": "error", "message": "Debes autenticarte"}, status=status.HTTP_401_UNAUTHORIZED)
        
        data = request.data.copy()

        response, error, status_response = ChatRoomService.perfom_send_message(player, chatroom_id, data)

        if error:
            return Response(data={
                'status': 'error',
                'message': error
            }, status=status_response)
        
        return Response({'status': 'success', "data": response}, status=status.HTTP_200_OK)
    
    @staticmethod
    def process_join(request, chatroom_id):
        try:
            player = Player.objects.get(user__id= request.user.id)
        except:
            return Response({"status": "error", "message": "Debes autenticarte"}, status=status.HTTP_401_UNAUTHORIZED)
        
        if player.is_block:
            return Response({'status': 'error', "message":"Este player esta bloqueado, contacta con los administradores"}, status=status.HTTP_409_CONFLICT)

        
        try:
            chatroom = ChatRoom.objects.get(id = chatroom_id)
        except:
            return Response({'status': 'error', "message":"Este chat no existe."}, status=status.HTTP_404_NOT_FOUND)
        
        check_player = chatroom.users_list.filter(player__id = player.id).exists()
        if not check_player:
            chatroom.users_list.add(player)

        serializer = ChatRoomRetrieveSerializer(chatroom)
        serializer.context['player_request'] = player
        return Response({'status': 'success', "data":serializer.data}, status=status.HTTP_200_OK)

    @staticmethod
    def process_exit(request, chatroom_id):
        try:
            player = Player.objects.get(user__id= request.user.id)
        except:
            return Response({"status": "error", "message": "Debes autenticarte"}, status=status.HTTP_401_UNAUTHORIZED)
        
        if player.is_block:
            return Response({'status': 'error', "message":"Este player esta bloqueado, contacta con los administradores"}, status=status.HTTP_409_CONFLICT)
        
        try:
            chatroom = ChatRoom.objects.get(id = chatroom_id)
        except:
            return Response({'status': 'error', "message":"Este chat no existe."}, status=status.HTTP_404_NOT_FOUND)
        
        check_player = chatroom.users_list.filter(player__id = player.id).exists()
        if check_player:
            chatroom.users_list.remove(player)

        return Response(status=status.HTTP_204_NO_CONTENT)
