from rest_framework import status
from dominoapp.utils.api_http import RequestValidator

class PlayerRequest:

    @staticmethod
    def validate_retrieve(player_id):
        is_valid = False
        message = None
        status_response = None

        is_valid = RequestValidator.validate_numeric(player_id)

        if not is_valid:
            message = "Player ID have wrong value"
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response       

        return True, message, status_response
    
    @staticmethod
    def validate_create(request):
        is_valid = False
        message = None
        status_response = None

        required_keys = [
            "email",
            "alias"
        ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "email": RequestValidator.validate_email,
            "alias": RequestValidator.validate_string,
            "phone": RequestValidator.validate_phone_number,
            "photo_url": RequestValidator.validate_url,
            "name": RequestValidator.validate_string,
            "lat": RequestValidator.validate_decimal,
            "lng": RequestValidator.validate_decimal,
            "timezone": RequestValidator.validate_text,
            "send_game_notifications": RequestValidator.validate_boolean
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response       

        return True, message, status_response
    
    @staticmethod
    def validate_update(request, is_partial):
        is_valid = False
        message = None
        status_response = None

        if not is_partial:
            required_keys = [
                "email",
                "alias"
            ]

            is_valid, message = RequestValidator.validate_required_key(request, required_keys)
            if not is_valid:
                message = message
                status_response = status.HTTP_400_BAD_REQUEST
                return is_valid, message, status_response

        validators = {
            "email": RequestValidator.validate_email,
            "phone": RequestValidator.validate_phone_number,
            "alias": RequestValidator.validate_string,
            "photo_url": RequestValidator.validate_url,
            "name": RequestValidator.validate_string,
            "lat": RequestValidator.validate_decimal,
            "lng": RequestValidator.validate_decimal,
            "timezone": RequestValidator.validate_text,
            "send_game_notifications": RequestValidator.validate_boolean
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response       

        return True, message, status_response
    
    @staticmethod
    def validate_login(request):
        is_valid = False
        message = None
        status_response = None
        
        required_keys = [
            "token"
        ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "token": RequestValidator.validate_string,
            "refer_code": RequestValidator.validate_short_uuid,
            "fcm_token": RequestValidator.validate_text
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response       

        return True, message, status_response
    
    @staticmethod
    def validate_fcm_register(request):
        is_valid = False
        message = None
        status_response = None
        
        required_keys = [
            "fcm_token"
        ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "fcm_token": RequestValidator.validate_text
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response       

        return True, message, status_response
    
    @staticmethod
    def validate_send_notification(request):
        is_valid = False
        message = None
        status_response = None
        
        required_keys = [
            "text",
            "title"
        ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "player_id": RequestValidator.validate_numeric,
            "text": RequestValidator.validate_text,
            "title": RequestValidator.validate_text
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response       

        return True, message, status_response
    
    
    @staticmethod
    def validate_rankin(request):
        is_valid = False
        message = None
        status_response = None
        
        validators = {
            "ordering": RequestValidator.validate_string,
            "page": RequestValidator.validate_numeric,
            "page_size": RequestValidator.validate_numeric
        }
        
        is_valid, message = RequestValidator.validate_query_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response       

        return True, message, status_response