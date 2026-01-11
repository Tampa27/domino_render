from rest_framework import status
from dominoapp.utils.api_http import RequestValidator


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
      