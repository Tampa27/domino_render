from google.oauth2 import id_token, service_account
from google.auth.transport import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
from django.conf import settings
from django.core.files.storage import Storage
from dotenv import load_dotenv
import io
import os
import json
import logging
logger = logging.getLogger('django')
load_dotenv('.env', override=True)

class GoogleTokenVerifier:
    @staticmethod
    def verify(token, device:str=None):
        GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
        GOOGLE_CLIENT_ID_WEB = os.getenv('GOOGLE_CLIENT_ID_WEB')
        try:
            if device == 'web':
                # Especifica el CLIENT_ID de la app web que accede al backend
                idinfo = id_token.verify_oauth2_token(
                    token, 
                    requests.Request(), 
                    GOOGLE_CLIENT_ID_WEB
                )

                # Verifica que el token sea emitido para tu cliente
                if idinfo['aud'] != GOOGLE_CLIENT_ID_WEB:
                    raise ValueError("El token no fue emitido para este cliente")
            else:
                # Especifica el CLIENT_ID de la app que accede al backend
                idinfo = id_token.verify_oauth2_token(
                    token, 
                    requests.Request(), 
                    GOOGLE_CLIENT_ID
                )
                # Verifica que el token sea emitido para tu cliente
                if idinfo['aud'] != GOOGLE_CLIENT_ID:
                    raise ValueError("El token no fue emitido para este cliente")

                
        except ValueError as e:
            logger.critical(f'Google Token is wront => {str(e)}')
            return None, e
        
        try:
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
            logger.critical(f'Google Verification is wront => {str(e)}')
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

        query = f"name= '{file_name}' and trashed=false and '{GoogleDrive.GOOGLE_DRIVE_FOLDER_ID}' in parents"
        
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

class GoogleDriveStorage(Storage):
    def __init__(self):
        creds_json = json.loads(os.getenv('GOOGLE_DRIVE_CREDS'))
        self.credentials = service_account.Credentials.from_service_account_info(creds_json)
        self.service = build('drive', 'v3', credentials=self.credentials)
        self.folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_MEDIA_ID')
        

    def _save(self, name, content):
        base_name = os.path.basename(name)
        folder_path = os.path.dirname(name)
        parent_id = self.folder_id
        
        # Crear estructura de carpetas si es necesario
        if folder_path:
            folders = folder_path.split('/')
            for folder in folders:
                if folder:  # Ignorar strings vacíos
                    # Verificar si la carpeta ya existe
                    query = f"name='{folder}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
                    results = self.service.files().list(
                        q=query,
                        fields='files(id)',
                        pageSize=1
                    ).execute().get('files', [])
                    
                    if results:
                        parent_id = results[0]['id']
                    else:
                        # Crear nueva carpeta
                        folder_metadata = {
                            'name': folder,
                            'mimeType': 'application/vnd.google-apps.folder',
                            'parents': [parent_id]
                        }
                        new_folder = self.service.files().create(
                            body=folder_metadata,
                            fields='id'
                        ).execute()
                        parent_id = new_folder['id']
        # Subir el archivo a la carpeta correspondiente
        file_metadata = {
            'name': base_name,
            'parents': [parent_id]
        }
        
        content.seek(0)
        media = MediaIoBaseUpload(
            io.BytesIO(content.read()),
            mimetype=content.content_type,
            resumable=True
        )
        
        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            return name
        except HttpError as error:
            raise Exception(f'Error al subir a Google Drive: {error}')
    
    def exists(self, name):
        try:
            self._get_file_id(name)
            return True
        except Exception:
            return False
    
    
    def url(self, name):
        try:
            file_id = self._get_file_id(name)
            # Generar URL directa de visualización
            return f"https://drive.google.com/uc?export=view&id={file_id}"
            
            # O para descarga directa:
            # return f"https://drive.google.com/uc?id={file_id}&export=download"
        except Exception as error:
            logger.critical(f'Error al generar URL en Google Drive => {str(error)}')
            return '#'
    
    def delete(self, name):
        try:
            file_id = self._get_file_id(name)
            self.service.files().delete(fileId=file_id).execute()
        except Exception as error:
            logger.critical(f'Error al eliminar archivo en Google Drive => {str(error)}')
            
    
    def _get_file_id(self, name):
        # Extraer el nombre base del archivo
        base_name = os.path.basename(name)
        
        # Si hay subcarpetas en el upload_to, replicarlas en Drive
        folder_path = os.path.dirname(name)
        current_folder_id = self.folder_id
        
        # Navegar por la estructura de carpetas si existe
        if folder_path:
            folders = folder_path.split('/')
            for folder in folders:
                if folder:  # Ignorar strings vacíos
                    # Buscar la subcarpeta dentro del padre actual
                    query = f"name='{folder}' and mimeType='application/vnd.google-apps.folder' and '{current_folder_id}' in parents and trashed=false"
                    results = self.service.files().list(
                        q=query,
                        fields='files(id)',
                        pageSize=1
                    ).execute().get('files', [])
                    
                    if not results:
                        # Crear la carpeta si no existe
                        folder_metadata = {
                            'name': folder,
                            'mimeType': 'application/vnd.google-apps.folder',
                            'parents': [current_folder_id]
                        }
                        new_folder = self.service.files().create(
                            body=folder_metadata,
                            fields='id'
                        ).execute()
                        current_folder_id = new_folder['id']
                    else:
                        current_folder_id = results[0]['id']
        
        # Buscar el archivo en la carpeta final
        query = f"name='{base_name}' and '{current_folder_id}' in parents and trashed=false"
        results = self.service.files().list(
            q=query,
            fields='files(id)',
            pageSize=1
        ).execute().get('files', [])
        
        if results:
            return results[0]['id']
        raise FileNotFoundError(f"El archivo {name} no existe en Google Drive")
    
    def size(self, name):
        file_id = self._get_file_id(name)
        file = self.service.files().get(
            fileId=file_id,
            fields='size'
        ).execute()
        return int(file.get('size', 0))
    
    def get_available_name(self, name, max_length=None):
        if not self.exists(name):
            return name
        
        base, ext = os.path.splitext(name)
        counter = 1
        while True:
            new_name = f"{base}_{counter}{ext}"
            if not self.exists(new_name):
                return new_name
            counter += 1