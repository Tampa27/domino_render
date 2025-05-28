from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
import os
import logging

class GoogleTokenVerifier:
    @staticmethod
    def verify(token):
        logger = logging.getLogger('django')
        try:
            # Especifica el CLIENT_ID de la app que accede al backend
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )

            # Verifica que el token sea emitido para tu cliente
            if idinfo['aud'] != settings.GOOGLE_CLIENT_ID:
                raise ValueError("El token no fue emitido para este cliente")

            # Verifica que el email esté verificado
            if not idinfo.get('email_verified', False):
                raise ValueError("Email no verificado por Google")

            return {
                'email': idinfo['email'],
                'name': idinfo.get('name', ''),
                'google_id': idinfo['sub'],
                'picture': idinfo.get('picture', ''),
            }, None
        except Exception as e:
            logger.critical(f'Google Cliend is wront => {str(e)}')
            return None, e