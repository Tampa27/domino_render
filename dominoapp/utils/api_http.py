import base64
import datetime
import os
import re
import uuid
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import URLValidator, EmailValidator


class RequestValidator:

    @staticmethod
    def validate_required_key(request, required_keys: list[str]):
        for key in required_keys:
            if key not in request.data:
                message = f"The {key} field is required."
                return False, message
        return True, None

    @staticmethod
    def validate_params(request, validators: dict):
        for param, value in request.data.items():
            if param in validators:
                if callable(validators[param]):
                    validator = validators[param]
                    validator_args = []
                else:
                    validator, *validator_args = validators[param]

                if not validator(value, *validator_args):
                    message = f"The {param} field have wrong value."
                    return False, message
            else:
                message = f"The {param} field is not recognized."
                return False, message

        return True, None
    
    @staticmethod
    def validate_required_params(request, required_params: list[str]):
        for key in required_params:
            if key not in request.query_params:
                message = f"The {key} params is required."
                return False, message
        return True, None

    @staticmethod
    def validate_query_params(request, validators: dict):
        for param, value in request.query_params.items():
            if param in validators:
                if callable(validators[param]):
                    validator = validators[param]
                    validator_args = []
                else:
                    validator, *validator_args = validators[param]
                if not validator(value, *validator_args):
                    message = f"The parameter {param} have wrong value."
                    return False, message
            else:
                message = f"The parameter {param} is not recognized."
                return False, message

        return True, None

    @staticmethod
    def normalize_keys(params):
        normalized_params = {}
        for key, value in params.items():
            is_list_key = key.endswith('[]')
            normalized_key = key.rstrip('[]')
            if is_list_key and not isinstance(value, list):
                value = [value]
            normalized_params[normalized_key] = value
        return normalized_params

    @staticmethod
    def query_to_dict(query_dict):
        result = {}
        for key, value_list in query_dict.lists():
            if len(value_list) == 1:
                result[key] = value_list[0]
            else:
                result[key] = value_list
        return result

    @staticmethod
    def _check_token(request) -> bool:
        expected_token = os.environ['EXTERNAL_API_TOKEN']
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header:
            try:
                auth_type, encoded_auth_token = auth_header.split(' ', 1)
                if auth_type.lower() != 'basic':
                    return False
                decoded_auth_token = base64.b64decode(encoded_auth_token).decode()
                if decoded_auth_token.startswith(':'):
                    decoded_auth_token = decoded_auth_token[1:]
                return decoded_auth_token == expected_token
            except ValueError:
                return False
        return False

    @staticmethod
    def validate_string(value):
        if not isinstance(value, str):
            return False
        safe_pattern = re.compile(r'^[\w \-._ñ@*,]+$', re.UNICODE)
        if safe_pattern.match(value):
            return True
        else:
            return False

    @staticmethod
    def validate_phone_number(value):
        if not isinstance(value, str):
            return False
        safe_pattern = re.compile(r'^\+?\s*(\d\s*){8,15}$')
        if safe_pattern.match(value):
            return True
        else:
            return False

    @staticmethod
    def validate_text(value):
        if value == "":
            return True
        pattern = r'^[^\n<>]+$'
        if not isinstance(value, str):
            return False
        regex = re.compile(pattern, re.MULTILINE)
        return bool(regex.match(value))

    @staticmethod
    def allow_empty_string(value):
        return value is None or len(value) == 0

    @staticmethod
    def validate_json(value):
        return isinstance(value, dict)

    @staticmethod
    def validate_password(value):
        return isinstance(value, str) and len(value) >= 8

    @staticmethod
    def validate_integer(value):
        return isinstance(value, int)

    @staticmethod
    def validate_numeric(value):
        if isinstance(value, int):
            return True
        if isinstance(value, str):
            try:
                int(value)
                return True
            except ValueError:
                return False
        return False

    # @staticmethod
    # def validate_timezone(value):
    #     try:
    #         pytz.timezone(value)
    #         return True
    #     except UnknownTimeZoneError:
    #         return False

    @staticmethod
    def validate_boolean(value):
        try:
            if isinstance(value, bool):
                return True
            if isinstance(value, str):
                value = value.strip().lower()
                if value in ["true", "false"]:
                    return True
            return False
        except ValueError:
            return False

    @staticmethod
    def validate_uuid(value):
        try:
            if isinstance(value, str):
                uuid_test = uuid.UUID(value, version=4)
                return str(uuid_test) == value
            return False
        except ValueError:
            return False
        
    @staticmethod
    def validate_short_uuid(value):
        try:
            if isinstance(value, str):
                return len(value) == 6
            return False
        except Exception:
            return False

    @staticmethod
    def validate_url(value):
        url_validator = URLValidator()
        try:
            url_validator(value)
            return True
        except ValidationError:
            return False

    @staticmethod
    def validate_email(value):
        email_validator = EmailValidator()
        try:
            email_validator(value)
            return True
        except ValidationError:
            return False

    @staticmethod
    def validate_in_array(value, target_array):
        return value.lower() in [item[1].lower() for item in target_array]
    
    @staticmethod
    def validate_in_array_0(value, target_array):
        try:        
            return value.lower() in [item[0].lower() for item in target_array]
        except:
            # if the array is numeric
            return value in [str(item[0]) for item in target_array]

    @staticmethod
    def validate_double(value):
        pattern = re.compile(r'^\d+(\.\d{1,2})?$')
        return bool(re.match(pattern, str(value)))

    @staticmethod
    def validate_decimal(value):
        pattern = re.compile(r'^-?\d+(\.\d+)?$')
        return bool(re.match(pattern, str(value)))

    @staticmethod
    def validate_one_or_list(element_validator):
        def validate(value):
            if not isinstance(value, list):
                return element_validator(value)
            return all(element_validator(item) for item in value)
        return validate

    @staticmethod
    def validate_list(element_validator):
        def validate(value):
            if not isinstance(value, list):
                return False
            return all(element_validator(item) for item in value)
        return validate

    @staticmethod
    def validate_upload_file(value):
        if not isinstance(value, UploadedFile):
            return False
        return True


    @staticmethod
    def validate_min_length(value, min_length):
        if len(value) == 0:
            return True
        return isinstance(value, str) and len(value) >= min_length

    @staticmethod
    def validate_pattern(value, pattern):
        if not isinstance(value, str):
            return False
        regex = re.compile(pattern)
        return bool(regex.match(value))

    @staticmethod
    def validate_timestamp(value):
        if not isinstance(value, int):
            return False
        try:
            datetime.datetime.utcfromtimestamp(value)
            return True
        except ValueError:
            return False

    # @staticmethod
    # def validate_country(value):
    #     if not isinstance(value, str):
    #         return False
    #     try:  
    #         return value in countries
    #     except ValueError:
    #         return False  