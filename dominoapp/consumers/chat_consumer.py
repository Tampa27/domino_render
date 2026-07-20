import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from datetime import datetime
from dominoapp.models import Player
from dominoapp.utils import game_tools
from dominoapp.utils.constants import WSActions
from dominoapp.utils.api_http import RequestValidator
from dominoapp.services.chatroom_service import ChatRoomService
import logging
logger = logging.getLogger('django')

class ChatConsumer(AsyncWebsocketConsumer):
    connected_players = {}  # Mapeo game_id -> set de usuarios conectados

    def get_redis_key(self):
        return f"count_chat_{self.chat_id}"
    
    async def connect(self):

        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.room_group_name = f'chat_{self.chat_id}'
        try:
            # 1. Verificar si el usuario está autenticado
            self.user = self.scope["user"]
            
            if self.user.is_anonymous:
                # Si no está autenticado, cerramos la conexión (código 4003 es común para política)
                await self.close(code=4003, reason="Debe autenticarse")
                return
            
            self.connected_players.setdefault(f'chat_{self.chat_id}', set()).add(self.channel_name)
        except Exception as error:
            logger.error(f"Error al autenticar en el lobby.\n Error: {error}")
            await self.close(code=4003, reason="Algo falló en la autenticación. Vuelva a intentar.")
            return   
        

        # 1. Identificar si el cliente envió subprotocolos
        subprotocols = self.scope.get("subprotocols", [])

        # 2. Elegir qué protocolo aceptar (si el cliente envió 'access_token')
        accepted_protocol = None
        if "access_token" in subprotocols:
            accepted_protocol = "access_token"
        else:
            await self.close(code=4003, reason="El parámetro 'access_token' es obligatorio")
            return

        # 3. Importante: Pasar el protocolo al método accept
        await self.accept(subprotocol=accepted_protocol)

        # Unirse al grupo de la mesa
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
    
    async def disconnect(self, close_code):
        room_players = self.connected_players.get(f'chat_{self.chat_id}')
    
        if room_players is not None:
            # Eliminamos el socket específico, no el objeto user
            room_players.discard(self.channel_name)
            
            # 2. Si el set está vacío, es que ya no hay nadie en esta sala (en este worker)
            if not room_players:
                redis_key = self.get_redis_key()
                await self.channel_layer.connection(0).delete(redis_key)
                # Limpiamos el diccionario para no dejar llaves huérfanas en memoria RAM
                if f'chat_{self.chat_id}' in self.connected_players:
                    del self.connected_players[f'chat_{self.chat_id}']

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Maneja los mensajes recibidos desde la APK"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            # Manejar diferentes tipos de mensajes
            if message_type == WSActions.CHAT_MESSAGE:
                await self.send_message(data)
            elif message_type == WSActions.PING:
                await self.handle_ping()
            else:
                await self.send_error(f"Tipo de mensaje no soportado: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Formato JSON inválido")
        except Exception as e:
            logger.error(f"Error en receive: {e}")
            await self.send_error(f"Error interno: {str(e)}")

    async def send_message(self, data):
        """Maneja el envio de mensajes a un chat"""
        try:            
            # Aquí procesas el envio del mensaje
            if self.user.is_anonymous:
                await self.send_error(f"El player no está autenticado")
                return
            
            chat_id = self.scope['url_route']['kwargs']['chat_id']
            message = data.get('message')
            reply_to = data.get('reply_to')
                        
            is_valid = RequestValidator.validate_uuid(str(chat_id))

            if not is_valid:
                await self.send_error("Este Chat ID no es correcto.")
                return
            if reply_to:
                is_valid = RequestValidator.validate_uuid(str(reply_to))

                if not is_valid:
                    await self.send_error("El mensaje que intenta responder no es correcto.")
                    return
            
            is_valid = RequestValidator.validate_text(message)

            if not is_valid:
                await self.send_error("El mensaje tiene caracteres que no están permitidos.")
                return

            # Validar el envio con tu lógica
            error = await self.perform_send(chat_id, self.user.id, data)
            if error:
                await self.send_error(error)

        except Exception as e:
            logger.error(f"No se puede enviar el mensaje, error: {str(e)}")
            await self.send_error(f"Error al envial mensaje: {str(e)}")

    @database_sync_to_async
    def perform_send(self, chat_id, user_id, data):
        try:
            player =  Player.objects.get(user__id=user_id)
        except Player.DoesNotExist:
            return "Debe autenticarse para realizar esta acción"
        
        response, error, status_response = ChatRoomService.perfom_send_message(player, chat_id, data)
        return error

    async def handle_ping(self):
        """Maneja ping para mantener la conexión viva"""
        await self.send(text_data=json.dumps({
            "a": WSActions.PING,
            "d" : {"lt": str(datetime.now())}
        }))

    async def send_error(self, error_message):
        """Envía un mensaje de error al cliente"""
        await self.send(text_data=json.dumps({
            "a": WSActions.ERROR,
            "d": {"mg": error_message}
        }))

    async def chat_update(self, event):
        """"Envia el mensaje de actualizacion al WS."""
        await self.send(text_data=json.dumps(event['payload']))
