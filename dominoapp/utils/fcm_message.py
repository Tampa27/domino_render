from fcm_django.models import FCMDevice
from firebase_admin.messaging import Notification, MulticastMessage, send_each_for_multicast
from firebase_admin import get_app
from django.contrib.auth.models import User
from django.conf import settings
import logging
logger = logging.getLogger('django')


class FCMNOTIFICATION:
    @staticmethod
    def _app_name_from_provider(provider: str) -> str:
        provider = (provider or '').lower()
        return settings.FIREBASE_APP_BY_PROVIDER.get(
            provider, settings.DEFAULT_FIREBASE_APP_NAME
        )

    @staticmethod
    def _send_to_devices(devices_qs, app_name: str, title: str, body: str, data: dict = None):
        tokens = list(
            devices_qs.exclude(registration_id__isnull=True)
                      .exclude(registration_id__exact='')
                      .values_list('registration_id', flat=True)
        )
        if not tokens:
            return

        try:
            firebase_app = get_app(app_name)
        except Exception as e:
            logger.critical(f'No existe la app Firebase "{app_name}": {e}')
            return

        message = MulticastMessage(
            notification=Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()} or None,
            tokens=tokens,
        )

        try:
            response = send_each_for_multicast(message, app=firebase_app)
            # Limpieza de tokens inválidos
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        err_str = str(resp.exception).lower() if resp.exception else ''
                        if ('not a valid fcm registration token' in err_str
                                or 'requested entity was not found' in err_str
                                or 'unregistered' in err_str):
                            FCMDevice.objects.filter(registration_id=tokens[idx]).delete()
        except Exception as e:
            logger.critical(f'Error al enviar FCM (app={app_name}): {e}')

    @staticmethod
    def send_fcm_message(user: User, title:str, body:str, data:dict = None):

        try:
            try:
                provider = user.user_player.provider
            except:
                provider = ''
            app_name = FCMNOTIFICATION._app_name_from_provider(provider)

            devices = FCMDevice.objects.filter(user=user, active=True)
            FCMNOTIFICATION._send_to_devices(devices, app_name, title, body, data)
        except Exception as error:
            logger.critical(f'Error al enviar notificacion FCM" => {str(error)}')

    @staticmethod
    def send_fcm_message_by_users_list(users: list[int], title:str, body:str, data:dict = None):

        try:
            from dominoapp.models import Player

            grouped = {}
            # Partimos de Player y navegamos a user__id
            rows = (Player.objects
                    .filter(user__id__in=users)
                    .values_list('user__id', 'provider'))

            for user_id, provider in rows:
                app_name = FCMNOTIFICATION._app_name_from_provider(provider)
                grouped.setdefault(app_name, []).append(user_id)
            
            for app_name, user_ids in grouped.items():
                devices = FCMDevice.objects.filter(user__id__in=user_ids, active=True)
                FCMNOTIFICATION._send_to_devices(devices, app_name, title, body, data)
        except Exception as error:
            logger.critical(f'Error al enviar notificacion FCM a listas de usuarios" => {str(error)}')

    @staticmethod
    def send_fcm_global_message(title:str, body:str):
        """Envía a todos, agrupando por provider desde Player."""

        try:
            from dominoapp.models import Player

            grouped = {}
            rows = Player.objects.values_list('user__id', 'provider')
            for user_id, provider in rows:
                if user_id is None:
                    continue
                app_name = FCMNOTIFICATION._app_name_from_provider(provider)
                grouped.setdefault(app_name, []).append(user_id)

            for app_name, user_ids in grouped.items():
                devices = FCMDevice.objects.filter(user__id__in=user_ids, active=True)
                FCMNOTIFICATION._send_to_devices(devices, app_name, title, body)
        except Exception as error:
            logger.critical(f'Error al enviar FCM notificacion global" => {str(error)}')