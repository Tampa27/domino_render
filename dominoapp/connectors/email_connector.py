import os
import logging
import locale
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
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
    def email_inactive_players(player: Player, expiration_time):
        subject = f"⚠ Tu cuenta en Dominó Club está por expirar ⚠"
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_TIME, '')

        html_message = render_to_string('email/delete_inactive_player.html', {
            'name': player.name,
            'alias': player.alias,
            'expiration_time': expiration_time.strftime("%d-%m-%Y"),
            })
        text_content = strip_tags(html_message)
        
        return EmailConnector.django_send_email(
                [player.email],
                subject,
                from_email=EmailConnector.admin_email,
                text= text_content,
                html = html_message
            )
    
    @staticmethod
    def email_players_db_backup(players_data):
        subject = f"⚠ Salvado de Base de Datos - Dominó Club ⚠"
        
        current_date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        html_message = render_to_string('email/backups_db_player.html', {
            'current_date': current_date,
            'players': players_data,
            })
        text_content = strip_tags(html_message)
        
        return EmailConnector.django_send_email(
                [EmailConnector.admin_email],
                subject,
                from_email=EmailConnector.admin_email,
                text= text_content,
                html = html_message
            )
    

