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
            "tiles": RequestValidator.validate_string,
            "coins": RequestValidator.validate_integer,
            "points": RequestValidator.validate_integer,
            "dataWins": RequestValidator.validate_integer,
            "dataLoss": RequestValidator.validate_integer,
            "matchWins": RequestValidator.validate_integer,
            "matchLoss": RequestValidator.validate_integer,
            "lastTimeInSystem": RequestValidator.validate_timestamp,
            "photo_url": RequestValidator.validate_url,
            "name": RequestValidator.validate_string,
            "isPlaying": RequestValidator.validate_boolean,
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response       

        return True, message, status_response
    
    @staticmethod
    def validate_update(request, player_id, is_partial):
        is_valid = False
        message = None
        status_response = None

        is_valid = RequestValidator.validate_numeric(player_id)

        if not is_valid:
            message = "Player ID have wrong value"
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response 

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
            "alias": RequestValidator.validate_string,
            "tiles": RequestValidator.validate_string,
            "coins": RequestValidator.validate_integer,
            "points": RequestValidator.validate_integer,
            "dataWins": RequestValidator.validate_integer,
            "dataLoss": RequestValidator.validate_integer,
            "matchWins": RequestValidator.validate_integer,
            "matchLoss": RequestValidator.validate_integer,
            "lastTimeInSystem": RequestValidator.validate_timestamp,
            "photo_url": RequestValidator.validate_url,
            "name": RequestValidator.validate_string,
            "isPlaying": RequestValidator.validate_boolean,
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
            "refer_code": RequestValidator.validate_short_uuid

        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response       

        return True, message, status_response