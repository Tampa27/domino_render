from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger('django')

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
        logger.error(f"Error en send_ws_notification: {e}")