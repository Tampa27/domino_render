from rest_framework import status
from dominoapp.utils.api_http import RequestValidator
from dominoapp.models import DominoGame

class GameRequest:

    @staticmethod
    def validate_game_id(game_id):
        is_valid = False
        message = None
        status_response = None

        is_valid = RequestValidator.validate_numeric(game_id)

        if not is_valid:
            message = "Game ID have wrong value"
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response       

        return True, message, status_response
    
    @staticmethod
    def validate_create(request):
        is_valid = False
        message = None
        status_response = None

        required_keys = [
            "variant"
        ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "variant": (RequestValidator.validate_in_array, DominoGame.variant_choices),
            "next_player": RequestValidator.validate_integer,
            "maxScore": RequestValidator.validate_integer,
            "inPairs": RequestValidator.validate_boolean,
            "perPoints": RequestValidator.validate_boolean,
            "startWinner": RequestValidator.validate_boolean,
            "lostStartInTie": RequestValidator.validate_boolean,
            "starter": RequestValidator.validate_integer,
            "payPassValue": RequestValidator.validate_integer,
            "payWinValue": RequestValidator.validate_integer,
            "payMatchValue": RequestValidator.validate_integer,
            "sumAllPoints": RequestValidator.validate_boolean,
            "capicua":RequestValidator.validate_boolean,
            "moveTime":RequestValidator.validate_integer,
            "password":RequestValidator.validate_password,
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response
    
    @staticmethod
    def validate_move(request, game_id):
        is_valid = False
        message = None
        status_response = None

        is_valid = RequestValidator.validate_numeric(game_id)

        if not is_valid:
            message = "Game ID have wrong value"
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        required_keys = [
            "tile"
        ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "tile": RequestValidator.validate_string
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response
    
    @staticmethod
    def validate_setwinner(request, game_id):
        is_valid = False
        message = None
        status_response = None

        is_valid = RequestValidator.validate_numeric(game_id)

        if not is_valid:
            message = "Game ID have wrong value"
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        required_keys = [
            "winner"
        ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "winner": RequestValidator.validate_numeric
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response

    @staticmethod
    def validate_setstarter(request, game_id):
        is_valid = False
        message = None
        status_response = None

        is_valid = RequestValidator.validate_numeric(game_id)

        if not is_valid:
            message = "Game ID have wrong value"
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        required_keys = [
            "starter"
        ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "starter": RequestValidator.validate_numeric
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response

    @staticmethod
    def validate_setwinnerstarter(request, game_id):
        is_valid = False
        message = None
        status_response = None

        is_valid = RequestValidator.validate_numeric(game_id)

        if not is_valid:
            message = "Game ID have wrong value"
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        required_keys = [
            "winner",
            "starter"
        ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "winner": RequestValidator.validate_numeric,
            "starter": RequestValidator.validate_numeric
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response

    @staticmethod
    def validate_setwinnerstarternext(request, game_id):
        is_valid = False
        message = None
        status_response = None

        is_valid = RequestValidator.validate_numeric(game_id)

        if not is_valid:
            message = "Game ID have wrong value"
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        required_keys = [
            "winner",
            "starter",
            "next_player"
        ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "winner": RequestValidator.validate_numeric,
            "starter": RequestValidator.validate_numeric,
            "next_player": RequestValidator.validate_numeric
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response

    @staticmethod
    def validate_setPatner(request, game_id):
        is_valid = False
        message = None
        status_response = None

        is_valid = RequestValidator.validate_numeric(game_id)

        if not is_valid:
            message = "Game ID have wrong value"
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        required_keys = [
            "patner_id"
        ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "patner_id": RequestValidator.validate_numeric
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response