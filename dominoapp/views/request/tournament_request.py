from rest_framework import status
from dominoapp.utils.api_http import RequestValidator
from dominoapp.utils.constants import GameVariants

class TournamentRequest:

    @staticmethod
    def validate_create(request):
        is_valid = False
        message = None
        status_response = None

        required_keys = [
            "variant",
            "winner_payout",
            "second_payout",
            "deadline",
            "start_at"
        ]

        is_valid, message = RequestValidator.validate_required_key(request, required_keys)
        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response

        validators = {
            "variant": (RequestValidator.validate_in_array_0, GameVariants.variant_choices),
            "maxScore": RequestValidator.validate_numeric,
            "inPairs": RequestValidator.validate_boolean,
            "startWinner": RequestValidator.validate_boolean,
            "moveTime": RequestValidator.validate_numeric,
            "min_player": RequestValidator.validate_numeric,
            "max_player": RequestValidator.validate_numeric,
            "active": RequestValidator.validate_boolean,
            "deadline": RequestValidator.validate_timestamp,
            "start_at": RequestValidator.validate_timestamp,
            "winner_payout": RequestValidator.validate_numeric,
            "second_payout": RequestValidator.validate_numeric,
            "third_payout": RequestValidator.validate_numeric,
            "registration_fee": RequestValidator.validate_numeric,
            "number_match_win": RequestValidator.validate_numeric
        }
        
        is_valid, message = RequestValidator.validate_params(request, validators)

        if not is_valid:
            message = message
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response     

        return True, message, status_response


    @staticmethod
    def validate_tournament_id(tournament_id):
        is_valid = False
        message = None
        status_response = None

        is_valid = RequestValidator.validate_numeric(tournament_id)

        if not is_valid:
            message = "Tournament ID have wrong value"
            status_response = status.HTTP_400_BAD_REQUEST
            return is_valid, message, status_response       

        return True, message, status_response
    