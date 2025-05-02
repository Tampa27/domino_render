from rest_framework import status
from dominoapp.utils.api_http import RequestValidator


class PaymentRequest:

    @staticmethod
    def validate_payments(request):
        is_valid = False
        message = None
        status_response = None

        required_keys = [
            "coins",
            "alias"
        ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "coins": RequestValidator.validate_numeric,
            "alias": RequestValidator.validate_string
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response
    