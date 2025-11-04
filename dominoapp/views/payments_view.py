from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from dominoapp.models import Transaction
from dominoapp.views.request.payments_request import PaymentRequest
from dominoapp.services.payments_service import PaymentService
from dominoapp.utils.request_permitions import IsSuperAdminUser
from drf_spectacular.utils import extend_schema, inline_serializer,OpenApiParameter, OpenApiExample
from rest_framework.serializers import BooleanField, IntegerField, CharField, ListField, UUIDField 


class PaymentView(viewsets.GenericViewSet):
    queryset = Transaction.objects.all()
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["recharge", "extract"]:
            permission_classes = [IsAdminUser]
        elif self.action in ["resume_game"]:
            permission_classes = [AllowAny]
        elif self.action in ['promotion']:
            permission_classes = [IsSuperAdminUser]       
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    @extend_schema(
            operation_id="payments_recharge",
            request = {
                200: inline_serializer(
                    name="Payments Recharge Request",
                    fields={
                        "coins" : IntegerField(required=True),
                        "alias": CharField(required=True),
                        "external_id": CharField(required=False),
                        "paymentmethod": CharField(required=False, help_text="saldo, transferencia")
                    }
                )
            },
            responses={
            200: inline_serializer(
                name="Payments Recharge Response",
                fields={
                    "status": CharField(default="success"),
                    "message": CharField()
                    },
            ),
            404: inline_serializer(
                name="Payments Recharge Response Error",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            
        }
    )
    @action(detail=False, methods=["post"])
    def recharge(self, request, pk = None):

        is_valid, message, status_response = PaymentRequest.validate_payments(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PaymentService.process_recharge(request)

    @extend_schema(
            operation_id="payments_request_recharge",
            request = {
                200: inline_serializer(
                    name="Payments Request Recharge",
                    fields={
                        "coins" : IntegerField(required=True),
                        "phone": CharField(required=True)
                    }
                )
            },
            responses={
            200: inline_serializer(
                name="Payments Request Recharge Response",
                fields={
                    "status": CharField(default="success"),
                    'transaction_id': CharField(max_length=6, min_length=6)
                    },
            ),
            404: inline_serializer(
                name="Payments Request Recharge Response Error",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            
        }
    )
    @action(detail=False, methods=["post"])
    def request_recharge(self, request, pk = None):

        is_valid, message, status_response = PaymentRequest.validate_request_recharge(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PaymentService.process_request_recharge(request)
    
    @extend_schema(
            operation_id="payments_promotion",
            request = {
                200: inline_serializer(
                    name="Payments Promotion Request",
                    fields={
                        "coins" : IntegerField(required=True),
                        "alias": CharField(required=True)
                    }
                )
            },
            responses={
            200: inline_serializer(
                name="Payments Promotion Response",
                fields={
                    "status": CharField(default="success"),
                    "message": CharField()
                    },
            ),
            404: inline_serializer(
                name="Payments Promotion Response Error",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            
        }
    )
    @action(detail=False, methods=["post"])
    def promotion(self, request, pk = None):

        is_valid, message, status_response = PaymentRequest.validate_promotions(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PaymentService.process_promotions(request)

    @extend_schema(
            operation_id="payments_extract",
            request = {
                200: inline_serializer(
                    name="Payments Extract Request",
                    fields={
                        "coins" : IntegerField(required=True),
                        "alias": CharField(required=True),
                        "external_id": CharField(required=False),
                        "paymentmethod": CharField(required=False, help_text="saldo, transferencia")
                    }
                )
            },
            responses={
            200: inline_serializer(
                name="Payments Extract Response",
                fields={
                    "status": CharField(default="success"),
                    "message": CharField()
                    },
            ),
            404: inline_serializer(
                name="Payments Extract Response Error",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            409: inline_serializer(
                name="Payments Extract Response Error 2",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            
        }
    )
    @action(detail=False, methods=["post"])
    def extract(self, request, pk = None):

        is_valid, message, status_response = PaymentRequest.validate_payments(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PaymentService.process_extract(request)
    
    @extend_schema(
            operation_id="payments_request_extraction",
            request = {
                200: inline_serializer(
                    name="Payments Request Extraction",
                    fields={
                        "coins" : IntegerField(required=True),
                        "card_number": CharField(required=True, min_length=16,max_length=16),
                        "phone": CharField(required=True)
                    }
                )
            },
            responses={
            200: inline_serializer(
                name="Payments Request Extraction Response",
                fields={
                    "status": CharField(default="success"),
                    'transaction_id': CharField(max_length=6, min_length=6)
                    },
            ),
            404: inline_serializer(
                name="Payments Request Extraction Response Error",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            409: inline_serializer(
                name="Payments Request Extract Response Error 2",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            
        }
    )
    @action(detail=False, methods=["post"])
    def request_extract(self, request, pk = None):

        is_valid, message, status_response = PaymentRequest.validate_request_extraction(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PaymentService.process_request_extraction(request)
    
    @extend_schema(
            operation_id="payments_transfer",
            request = {
                200: inline_serializer(
                    name="Payments Transfer Request",
                    fields={
                        "amount" : IntegerField(required=True),
                        "to_user": IntegerField(required=True),
                    }
                )
            },
            responses={
            200: inline_serializer(
                name="Payments Recharge Response",
                fields={
                    "status": CharField(default="success"),
                    "message": CharField()
                    },
            ),
            404: inline_serializer(
                name="Payments Transfer Response 404",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            409: inline_serializer(
                name="Payments Transfer Response 409",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            
        }
    )
    @action(detail=False, methods=["post"])
    def transfer(self, request, pk = None):

        is_valid, message, status_response = PaymentRequest.validate_transfer(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PaymentService.process_transfer(request)
    
    @action(detail=False, methods=["get"])
    def resume_game(self, request, pk = None):

        is_valid, message, status_response = PaymentRequest.validate_resume_game(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PaymentService.process_resume_game(request)

    @extend_schema(
            operation_id="payments_create",
            request = {
                200: inline_serializer(
                    name="Payments Create Request",
                    fields={
                        "amount" : IntegerField(required=True)
                    }
                )
            },
            responses={
            200: inline_serializer(
                name="Payments Create Response",
                fields={
                    "status": CharField(default="success"),
                    "message": CharField()
                    },
            ),
            404: inline_serializer(
                name="Payments Create Response Error",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            
        }
    )
    def create(self, request, pk = None):

        is_valid, message, status_response = PaymentRequest.validate_payments_create(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PaymentService.process_payment(request)
    
    @extend_schema(
            operation_id="paypal_capture",
            request = {
                200: inline_serializer(
                    name="Paypal Capture Request",
                    fields={
                        "external_id": CharField(required=True)
                    }
                )
            },
            responses={
            200: inline_serializer(
                name="Paypal Capture Response",
                fields={
                    "status": CharField(default="success"),
                    "message": CharField()
                    },
            ),
            404: inline_serializer(
                name="Paypal Capture Response Error",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            
        }
    )
    @action(detail=False, methods=["post"])
    def paypalcapture(self, request, pk = None):

        is_valid, message, status_response = PaymentRequest.validate_paypal_capture(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PaymentService.process_payment(request)
    
