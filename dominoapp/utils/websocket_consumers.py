import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging
logger = logging.getLogger('django')

class GameConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.room_group_name = f'g_{self.game_id}'

        # Unirse al grupo de la mesa
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        pass  # En este caso, el servidor no espera recibir mensajes del cliente, pero podrías manejarlo aquí si lo necesitas


    async def game_update(self, event):
        # Envía el mensaje de actualización a los clientes conectados a esta mesa
        payload = event['payload']
        await self.send(text_data=json.dumps(payload))


def send_ws_notification(game_id, payload):
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'g_{game_id}',
            {
                "type": "game_update",
                "payload": payload
            }
        )
    except Exception as e:
        logger.error(f"Error en el on_commit de send_ws_notification : {e}")