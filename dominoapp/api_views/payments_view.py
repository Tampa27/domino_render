from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, AllowAny
from dominoapp.models import Transaction
from dominoapp.api_views.request.payments_request import PaymentRequest
from dominoapp.services.payments_service import PaymentService
from drf_spectacular.utils import extend_schema, inline_serializer,OpenApiParameter, OpenApiExample
from rest_framework.serializers import BooleanField, IntegerField, CharField, ListField, UUIDField 


class PaymentView(viewsets.GenericViewSet):
    queryset = Transaction.objects.all()
    permission_classes = [IsAdminUser]

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
    
    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def resume_game(self, request, pk = None):

        is_valid, message, status_response = PaymentRequest.validate_resume_game(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PaymentService.process_resume_game(request)