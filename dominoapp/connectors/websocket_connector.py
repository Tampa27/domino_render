"""
Estos WEBSOCKET lo dejo para mas alante implementar y sustituir por los PUSHER
WEBSOCKET es mas economico que los PUSHER
"""
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.layers import get_channel_layer
from datetime import datetime

async def test_connection():
    channel_layer = get_channel_layer()
    try:
        # Usamos una operación real que existe en el channel_layer
        await channel_layer.send("test_channel", {"type": "test.message", "text": "ping"})
        
        print("✅ Conexión exitosa con Redis Cloud")
        return True
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        return False
        
    

from asgiref.sync import async_to_sync

def notificar_inicio_juego(mesa_id):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'mesa_{mesa_id}',
        {
            'type': 'start_game',
            'mesa_id': mesa_id,
            'mensaje': 'El juego ha comenzado!'
        }
    )

def notificar_jugador_unido(mesa_id, jugador_id):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"mesa_{mesa_id}",
        {
            'type': 'jugador_unido',
            'jugador_id': jugador_id,
            'mesa_id': mesa_id
        }
    )
    print("conexion exitosa")
    return True




class DominoConsumer(AsyncWebsocketConsumer):
    # channel_layer = get_channel_layer()
    
    async def connect(self):
        print("estoy en connect")
        print("kwars: ", self.scope['url_route']['kwargs'])
        self.mesa_id = self.scope['url_route']['kwargs']['game_id']
        self.jugador_id = self.scope['url_route']['kwargs']['player']
        self.grupo_mesa = f'mesa_{self.mesa_id}'
        
        # Unirse al grupo
        await self.channel_layer.group_add(
            self.grupo_mesa,
            self.channel_name
        )
        await self.accept()

        # Notificar a todos que un jugador se unió
        await self.channel_layer.group_send(
            self.grupo_mesa,
            {
                'type': 'new_player',
                'player': self.jugador_id,
                'game_id': self.mesa_id,
                'accion': 'conexion',
                'mensaje': f'Jugador {self.jugador_id} se ha unido a la mesa'
            }
        )

    async def disconnect(self, close_code):
        # Salir del grupo
        await self.channel_layer.group_send(
            self.grupo_mesa,
            {
                'type': 'exit_player',
                'player': self.jugador_id,
                'game_id': self.mesa_id,
                'accion': 'desconexion',
                'mensaje': f'Jugador {self.jugador_id} abandonó la mesa'
            }
        )
        
        # Salir del grupo
        await self.channel_layer.group_discard(
            self.grupo_mesa,
            self.channel_name
        )

        await super().disconnect(close_code)

    async def movimiento_ficha(self, event):
        # Enviar mensaje a WebSocket
        await self.send(text_data=json.dumps({
            'type': 'movement_tile',
            'player': event['player'],
            'tile': event['tile'],
            'next_player': event['next_player'],
            'time': event['time']
        }))

    async def jugador_unido(self, event):
        # Enviar notificación a todos los clientes
    
        self.send(text_data=json.dumps({
            'type': 'join_player',
            'player': event['player'],
            'game_id': event['game_id'],
            'mensaje': event['mensaje']
        }))

        await self.connect()
        print("✅ Conexión exitosa con Redis Cloud")
        return True
        


    async def jugador_abandono(self, event):
        await self.send(text_data=json.dumps({
            'type': 'exit_player',
            'player': event['player'],
            'game_id': event['game_id'],
            'mensaje': event['mensaje']
        }))

    async def juego_iniciado(self, event):
        await self.send(text_data=json.dumps({
            'type': 'start_game',
            'game_id': event['game_id'],
            'mensaje': event['mensaje'],
            'time': str(datetime.now())
        }))

    async def finalizar_data(self, event):
        await self.send(text_data=json.dumps({
            'type': 'finish_data',
            'game_id': event['game_id'],
            'mensaje': event['mensaje'],
            'time': str(datetime.now())
        }))

    async def finalizar_partida(self, event):
        await self.send(text_data=json.dumps({
            'type': 'finish_game',
            'game_id': event['game_id'],
            'mensaje': event['mensaje'],
            'time': str(datetime.now())
        }))