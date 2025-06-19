from google.oauth2 import id_token, service_account
from google.auth.transport import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django.conf import settings
from dotenv import load_dotenv
import os
import json
import logging
logger = logging.getLogger('django')
load_dotenv('.env', override=True)

class GoogleTokenVerifier:
    @staticmethod
    def verify(token):
        
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
        
class GoogleDrive:
    # Configura las credenciales
    GOOGLE_DRIVE_SCOPE = os.getenv('GOOGLE_DRIVE_SCOPE', '')
    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')
    SCOPES = [GOOGLE_DRIVE_SCOPE]
    GOOGLE_DRIVE_CREDS = os.getenv("GOOGLE_DRIVE_CREDS")

    
    staticmethod
    def get_drive_service():
        
        if not GoogleDrive.GOOGLE_DRIVE_CREDS:
            raise ValueError("GOOGLE_DRIVE_CREDS no está configurado en las variables de entorno.")
        creds_info = json.loads(GoogleDrive.GOOGLE_DRIVE_CREDS)
        
        try:
            creds = service_account.Credentials.from_service_account_info(
                creds_info, scopes=GoogleDrive.SCOPES)
            return build('drive', 'v3', credentials=creds)
        except Exception as error:
            logger.critical(f'Google Drive Credentials is wront => {str(error)}')
    
    staticmethod
    def upload_file(file_path, file_name):
        """Sube un archivo a Google Drive"""
        service = GoogleDrive.get_drive_service()
        
        file_metadata = {
            'name': file_name,
            'parents': [GoogleDrive.GOOGLE_DRIVE_FOLDER_ID] 
        }
                
        media = MediaFileUpload(file_path, resumable=True)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        return file
    
    staticmethod
    def delete_old_file(file_name, file_id):
        """Elimina archivos antiguos con el mismo file_name pero que tengan diferente file_id"""
        service = GoogleDrive.get_drive_service()

        query = f"name= '{file_name}' and trashed=false and {GoogleDrive.GOOGLE_DRIVE_FOLDER_ID} in parents"
        
        try:
            results = service.files().list(
                q=query,
                fields="files(id, name)").execute()
            files = results.get('files', [])
            
            for file in files:
                try:
                    if file['id'] != file_id:
                        service.files().delete(fileId=file['id']).execute()
                        
                except Exception as error:
                    logger.critical(f"No se pudo eliminar {file['name']} en Google Drive => {str(error)}")
        except Exception as error:
            logger.critical(f'Error al buscar archivos en Google Drive => {str(error)}')