from rest_framework import status
from dominoapp.utils.api_http import RequestValidator
from dominoapp.utils.constants import TransactionPaymentMethod


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
            "alias": RequestValidator.validate_string,
            "external_id": RequestValidator.validate_string,
            "paymentmethod": (RequestValidator.validate_in_array_0, TransactionPaymentMethod.payment_choices)
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response
    
    @staticmethod
    def validate_promotions(request):
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
    
    @staticmethod
    def validate_resume_game(request):
        is_valid = False
        message = None
        status_response = None

        params_validators = {
            "alias": RequestValidator.validate_string,
            "game_id": RequestValidator.validate_numeric,
            "from_at": RequestValidator.validate_timestamp,
            "to_at": RequestValidator.validate_timestamp,
            "traceback": RequestValidator.validate_boolean
        }
        
        is_valid, message = RequestValidator.validate_query_params(request, params_validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response