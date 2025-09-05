import os
import pusher
import logging

logger = logging.getLogger('django')

class PushNotificationConnector:
    try:
        pusher_client = pusher.Pusher(
            app_id=os.getenv("PUSHER_APP_ID"),
            key=os.getenv("PUSHER_KEY"),
            secret=os.getenv("PUSHER_SECRET"),
            cluster='mt1',
            ssl=True
        )
    except:
        pusher_client = None
    
    @staticmethod
    def push_notification(channel, event_name, data_notification, socket_id= None):
        """
        Enviar notificaciones PUSHER desde el server para la apk\n
        **channel** = 'mesa_{*game.id*}'\n
        **event_name** = `'create_game'` | `'move_tile'` | `'join_player'` | `'exit_player'` | `'start_game'` | `'end_game'`\n
        **data_notification**: `dic` con toda la informacion necesaria para la apk.
        """

        try:
            PushNotificationConnector.pusher_client.trigger(
                channels = channel,
                event_name = event_name,
                data = data_notification,
                socket_id = socket_id
            )
        except Exception as e:
            logger.critical(f"Error sending push notification, exception={e}")
            return False
        return True
