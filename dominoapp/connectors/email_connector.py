import os
import logging
import locale
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.html import strip_tags
from django.conf import settings
from datetime import datetime, timedelta
import base64
from io import BytesIO
from dominoapp.models import Player
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger('django')


class EmailConnector:
    admin_email = os.getenv("ADMIN_EMAIL")

    @staticmethod
    def django_send_email(to_email:list[str], subject:str, from_email:str= None, text:str=None, html:str=None):
        if not to_email:
            raise ValueError("Error sending email. The to_email parameter is required.")
        if not text and not html:
            raise ValueError("Error sending email. At least one of[text, html] parameter is required.")
        if not subject:
            raise ValueError("Error sending email. The subject parameter is required.")
        
        try:        
            send_mail(
                subject,
                message = text if text is not None else None,
                from_email= from_email if from_email is not None else None,
                recipient_list=to_email,
                html_message= html if html is not None else None
            )
            return True

        except Exception as e:
            print(
                f"Some Exception occured when sending an email to {to_email}. Details: {e.__str__()}"
            )
            logger.critical(f"Some Exception occured with django email. Details: {e.__str__()}")
            return False

    @staticmethod
    def email_inactive_players(player: Player):
        subject = f"⚠ Tu cuenta en Dominó Club está por expirar ⚠"

        locale.setlocale(locale.LC_TIME, 'spanish') 
        expiration_time = datetime.now() + timedelta(days=7)

        html_message = render_to_string('email/delete_inactive_player.html', {
            'name': player.name,
            'alias': player.alias,
            'expiration_time': expiration_time.strftime("%d de %B de %Y"),
            })
        text_content = strip_tags(html_message)
        
        return EmailConnector.django_send_email(
                [player.email],
                subject,
                from_email=EmailConnector.admin_email,
                text= text_content,
                html = html_message
            )