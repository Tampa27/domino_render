from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification
from django.contrib.auth.models import User
import logging
logger = logging.getLogger('django')


class FCMNOTIFICATION:

    @staticmethod
    def send_fcm_message(user: User, title:str, body:str):

        try:
            user_devices = FCMDevice.objects.filter(user=user)
            user_devices.send_message(
                Message(
                    notification=Notification(
                            title=title, 
                            body=body
                    )
                )
            )
        except Exception as error:
            logger.critical(f'Error al enviar notificacion FCM" => {str(error)}')