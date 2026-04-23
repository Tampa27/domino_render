import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from datetime import datetime
from dominoapp.models import Player
from dominoapp.utils import game_tools
from dominoapp.utils.constants import WSActions
import logging
logger = logging.getLogger('django')

class GameConsumer(AsyncWebsocketConsumer):
    connected_players = {}  # Mapeo game_id -> set de usuarios conectados

    def get_redis_key(self):
        return f"count_g_{self.game_id}"
    
    async def connect(self):

        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.room_group_name = f'g_{self.game_id}'
        try:
            # 1. Verificar si el usuario está autenticado
            self.user = self.scope["user"]
            
        #     if self.user.is_anonymous:
        #         # Si no está autenticado, cerramos la conexión (código 4003 es común para política)
        #         # await self.close(code=4003)
        #         # return
        #         pass  ## Por el momento permitimos conexiones anónimas para que no de error los procesos de desarrollo sin autenticación
            
        #     self.connected_players.setdefault(self.game_id, set()).add(self.user)
        except Exception as error:
            pass  ## Por el momento permitimos conexiones anónimas para que no de error los procesos de desarrollo sin autenticación 
        
        self.connected_players.setdefault(self.game_id, set()).add(self.channel_name)

        # 1. Identificar si el cliente envió subprotocolos
        subprotocols = self.scope.get("subprotocols", [])

        # 2. Elegir qué protocolo aceptar (si el cliente envió 'access_token')
        accepted_protocol = None
        if "access_token" in subprotocols:
            accepted_protocol = "access_token"

        # 3. Importante: Pasar el protocolo al método accept
        await self.accept(subprotocol=accepted_protocol)

        # Unirse al grupo de la mesa
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
    
    async def disconnect(self, close_code):
        room_players = self.connected_players.get(self.game_id)
    
        if room_players is not None:
            # Eliminamos el socket específico, no el objeto user
            room_players.discard(self.channel_name)
            
            # 2. Si el set está vacío, es que ya no hay nadie en esta sala (en este worker)
            if not room_players:
                # Limpiamos el diccionario para no dejar llaves huérfanas en memoria RAM
                if self.game_id in self.connected_players:
                    del self.connected_players[self.game_id]
                
                # 3. Borrar el contador de Redis
                async with self.channel_layer.connection(0) as conn:
                    await conn.delete(self.get_redis_key())

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
            if message_type == WSActions.TILE_MOVED:
                await self.handle_move(data)
            elif message_type == WSActions.CHAT_MESSAGE:
                pass
            elif message_type == WSActions.PING:
                await self.handle_ping()
            else:
                await self.send_error(f"Tipo de mensaje no soportado: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Formato JSON inválido")
        except Exception as e:
            logger.error(f"Error en receive: {e}")
            await self.send_error(f"Error interno: {str(e)}")

    async def handle_move(self, data):
        """Maneja un movimiento de ficha"""
        try:
            # Aquí procesas el movimiento
            game_id = self.scope['url_route']['kwargs']['game_id']
            move_tile = data.get('tile')
            
            if self.user.is_anonymous:
                await self.send_error(f"El player no esta autenticado")
                return
            
            # Validar el movimiento con tu lógica de negocio
            error = await self.perform_move(game_id, self.user.id, move_tile)
            if error:
                await self.send_error(error)

        except Exception as e:
            await self.send_error(f"Error al procesar movimiento: {str(e)}")

    @database_sync_to_async
    def perform_move(self, game_id, user_id, move_tile):
        try:
            player =  Player.objects.get(user__id=user_id)
        except Player.DoesNotExist:
            return "Debe autenticarse para realizar esta acción"
        
        return game_tools.move1(game_id, player, move_tile)

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

    async def game_update(self, event):
        """"Envia el mensaje de actualizacion al WS."""
        await self.send(text_data=json.dumps(event['payload']))
