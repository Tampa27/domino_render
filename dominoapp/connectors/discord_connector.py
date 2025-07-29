import logging
import os
import requests
from dominoapp.utils.constants import ApiConstants


class DiscordConnector:
    errors_url = os.environ.get('DISCORD_ERRORS_URL', '')
    events_url = os.environ.get('DISCORD_EVENTS_URL', '')
    environment = (os.environ.get('PRODUCTION', "True")=="True")
    
    @staticmethod
    def _make_request(url, payload):
        logger = logging.getLogger(__name__)
        try:
            res = requests.post(url, json=payload)
            if res.status_code != 204:
                logger.error(f'Failed to send message to Discord with status {res.status_code}. Payload: {payload}')
        except requests.RequestException as e:
            logger.error(f'DiscordConnector => {str(e)}')

    @staticmethod
    def send_error(message):
        if DiscordConnector.errors_url:
            start = "### 🚨 Oops! Something went wrong. 🚨\n```bash\n"
            end = "```"
            max_length = 2000 - (len(start) + len(end))
            content = message if len(message) <= max_length else f'{message[:max_length - 4]}\n...'

            payload = {
                "username": f'BACKEND API ({"Production" if DiscordConnector.environment else "Development"})',
                "content": f'{start}{content}{end}',
                "allowed_mentions": {"parse": ["everyone"]}
            }

            DiscordConnector._make_request(DiscordConnector.errors_url, payload)

    @staticmethod
    def send_event(event_type, params):
        if DiscordConnector.events_url:
            if event_type == ApiConstants.AdminNotifyEvents.ADMIN_EVENT_NEW_USER.key:
                content = f"🎉 Nuevo Usuario, Alerta! 🎉 \n Tenemos un usuario nuevo: {params.get('name')} ({params.get('email')})!"
            elif event_type == ApiConstants.AdminNotifyEvents.ADMIN_EVENT_NEW_RELOAD.key:
                content = f"🎉 Nueva Recarga, Alerta! 🎉 \n Hemos recibido una recarga de {params.get('player')} con un monto de {params.get('amount')} pesos!"
            elif event_type == ApiConstants.AdminNotifyEvents.ADMIN_EVENT_NEW_EXTRACTION.key:
                content = f"🎉 Nueva Extracción, Alerta! 🎉 \n Se a realizado una extraccion de {params.get('player')} con un monto de {params.get('amount')} pesos!"
            elif event_type == ApiConstants.AdminNotifyEvents.ADMIN_EVENT_EMAIL_DELETE_PLAYER.key:
                content = f":rotating_light:  Email de Eliminacion Enviado, Alerta! :rotating_light: \n Se ha enviado un email a la cuenta {params.get('email')} por inactividad, la cuenta sera eliminada dentro de 7 dias!"
            else:
                content = f":rotating_light: New Event! :rotating_light: Type: {event_type} - Details: {params}"

            payload = {
                "username": f'DOMINO CLUB ({"Production" if DiscordConnector.environment else "Development"})',
                "content": content,
                "allowed_mentions": {"parse": ["everyone"]}
            }

            DiscordConnector._make_request(DiscordConnector.events_url, payload)