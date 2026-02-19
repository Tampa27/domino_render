from rest_framework import status
from dominoapp.utils.api_http import RequestValidator
from dominoapp.utils.constants import ChatRoomTypes


class ChatRoomRequest:

    @staticmethod
    def validate_uuid(request, pk):
        is_valid = False
        message = None
        status_response = None
        
        is_valid = RequestValidator.validate_uuid(pk)

        if not is_valid:
            message = "Este Chat ID no es correcto."
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response 

        required_keys = []

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {}
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response
    
    @staticmethod
    def validate_create(request):
        is_valid = False
        message = None
        status_response = None
        
        required_keys = [
            "title",
            "users_list"
            ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "title": RequestValidator.validate_string,
            "users_list": RequestValidator.validate_list(RequestValidator.validate_numeric),
            "game_id": RequestValidator.validate_numeric,
            "room_type": (RequestValidator.validate_in_array_0, ChatRoomTypes.chatroom_choices)
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response
    
    @staticmethod
    def validate_create_message(request, chatroom_id):
        is_valid = False
        message = None
        status_response = None
        
        is_valid = RequestValidator.validate_uuid(chatroom_id)

        if not is_valid:
            message = "Este Chat ID no es correcto."
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response
        
        required_keys = [
            "message"
            ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "message": RequestValidator.validate_text,
            "reply_to": RequestValidator.validate_uuid
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response