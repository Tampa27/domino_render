import json
from channels.generic.websocket import AsyncWebsocketConsumer
from datetime import datetime
from dominoapp.utils.websocket_utils import async_get_count_lobby_up
from dominoapp.utils.constants import WSActions
from dominoapp.consumers.games_consumer import GameConsumer
import logging
logger = logging.getLogger('django')

class LobbyConsumer(AsyncWebsocketConsumer):
    connected_players = {}  # Mapeo lobby -> set de usuarios conectados

    def get_redis_key(self):
        return f"count_lobby"
    
    async def connect(self):

        self.room_group_name = f'lobby_group'

        # 1. Identificar si el cliente envió subprotocolos
        subprotocols = self.scope.get("subprotocols", [])
        if "access_token" not in subprotocols:
            await self.close(code=4003, reason="El parámetro 'access_token' es obligatorio")
            return
    
        self.user = self.scope.get("user")
        if self.user is None or self.user.is_anonymous:
            await self.close(code=4003, reason="Debe autenticarse")
            return

        # ---- 2. Aceptar handshake ----
        try:
            await self.accept(subprotocol="access_token")
        except Exception as error:
            logger.error(f"Error al aceptar el WS del lobby, Error->: {error}")
            return

         # ---- 3. Recién aquí mutamos presencia ----
        self.connected_players.setdefault("lobby", {})
        self.connected_players["lobby"][self.user.id] = (
            self.connected_players["lobby"].get(self.user.id, 0) + 1
        )

        # Unirse al grupo del lobby
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # ---- 5. Notificar ----
        try:
            await self.notify_connected_players_count()
        except Exception as error:
            logger.error(f"Error al notificar numero de players en el lobby.\n Error: {error}")
    
    async def disconnect(self, close_code):
        room_players = self.connected_players.get("lobby")
        user = getattr(self, "user", None)

        if room_players and user is not None and not user.is_anonymous:
            current = room_players.get(user.id, 0)
            if current <= 1:
                room_players.pop(user.id, None)   # era su última conexión
            else:
                room_players[user.id] = current - 1

            # Si ya no queda nadie en el lobby de este worker, limpiamos la llave
            if not room_players:
                self.connected_players.pop("lobby", None)
        
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        try:
            await self.notify_connected_players_count()
        except Exception as error:
            logger.error(f"Error al notificar numero de players en el lobby.\n Error: {error}")

    async def receive(self, text_data):
        """Maneja los mensajes recibidos desde la APK"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            # Manejar diferentes tipos de mensajes
            if message_type == WSActions.CHAT_MESSAGE:
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

    async def notify_connected_players_count(self):
        """Envía el conteo de jugadores al grupo"""
        lobby_count = len(self.connected_players.get("lobby", {}))

        # ✅ Obtener jugadores de todas las mesas
        games_count = GameConsumer.get_players_in_games()
        
        # Total de jugadores
        total_players = lobby_count + games_count
        
        payload = {
            "a": WSActions.CONNECTED_PLAYERS,
            "cg": await async_get_count_lobby_up(),
            "d": {
                "connected_players": total_players,                
            }
        }
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "lobby_update",
                "payload": payload
            }
        )

    async def lobby_update(self, event):
        """"Envia el mensaje de actualizacion al WS."""
        await self.send(text_data=json.dumps(event['payload']))
