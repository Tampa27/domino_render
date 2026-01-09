from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import OrderingFilter
from django.db.models import Q
from dominoapp.models import Transaction
from dominoapp.views.request.payments_request import PaymentRequest
from dominoapp.views.filters.payment_filter import PaymentSearchFilter
from dominoapp.services.payments_service import PaymentService
from dominoapp.serializers import ListTransactionsSerializer
from dominoapp.utils.request_permitions import IsSuperAdminUser
from drf_spectacular.utils import extend_schema, inline_serializer,OpenApiParameter, OpenApiExample
from rest_framework.serializers import BooleanField, IntegerField, CharField, ListField, UUIDField 

class PaymentListPagination(PageNumberPagination):
    page_size = 3
    page_size_query_param = "page_size"

class PaymentView(viewsets.GenericViewSet, mixins.ListModelMixin):
    queryset = Transaction.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = PaymentListPagination
    serializer_class = ListTransactionsSerializer
    filter_backends = [
        OrderingFilter,
        PaymentSearchFilter
        ]
    search_fields = ['type', 'from_user__alias', 'from_user__name', 'to_user__alias', 'to_user__name', 'status_list__status']

    def get_permissions(self):
        if self.action in ["recharge", "extract", "select", "confirm"]:
            permission_classes = [IsAdminUser]
        elif self.action in ["resume_game", "send_test_message"]:
            permission_classes = [AllowAny]
        elif self.action in ['promotion']:
            permission_classes = [IsSuperAdminUser]       
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if not user.is_superuser and not user.is_staff:
            queryset = Transaction.objects.filter(Q(from_user__user__id = user.id) | Q(to_user__user__id = user.id)).order_by("-time")
        else:
            queryset = Transaction.objects.all().exclude(type__in = ["gm","pro","tr"] ).order_by("-time")
        if self.action in ["select", "confirm", "cancel"]:
            queryset.exclude(type__in = ["gm","pro","tr"] )
        return queryset 
    
    @extend_schema(
            operation_id="payments_recharge",
            request = {
                "application/json": inline_serializer(
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
                "application/json": inline_serializer(
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
                "application/json": inline_serializer(
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
                "application/json": inline_serializer(
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
                "application/json": inline_serializer(
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
                "application/json": inline_serializer(
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
    
    @extend_schema(
            operation_id="payments_list",
            request = None,
            responses={
            200: ListTransactionsSerializer(many=True),            
        }
    )
    def list(self, request, pk = None):
        return mixins.ListModelMixin.list(self, request)
    
    @extend_schema(
            operation_id="payments_select",
            request = None,
            responses={
            204: None,
            404: inline_serializer(
                name="Payments Select Response 404",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            409: inline_serializer(
                name="Payments Select Response 409",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            
        }
    )
    @action(detail=True, methods=["post"])
    def select(self, request, pk = None):
        is_valid, message, status_response = PaymentRequest.validate_uuid(request, pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        return PaymentService.process_select(request, pk)
    
    @extend_schema(
            operation_id="payments_confirm",
            request = None,
            responses={
            204: None,
            404: inline_serializer(
                name="Payments Confirm Response 404",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            409: inline_serializer(
                name="Payments Confirm Response 409",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            
        }
    )
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk = None):
        is_valid, message, status_response = PaymentRequest.validate_uuid(request, pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        return PaymentService.process_confirm(request, pk)
    
    @extend_schema(
            operation_id="payments_cancel",
            request = None,
            responses={
            204: None,
            404: inline_serializer(
                name="Payments Cancel Response 404",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            409: inline_serializer(
                name="Payments Cancel Response 409",
                fields={
                    "status": CharField(default="error"),
                    "message": CharField()
                    },
            ),
            
        }
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk = None):
        is_valid, message, status_response = PaymentRequest.validate_uuid(request, pk)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        return PaymentService.process_cancel(request, pk)
    
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
                "application/json": inline_serializer(
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
                "application/json": inline_serializer(
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
    
    @action(detail=False, methods=["post"])
    def send_test_message(self, request):
        """Endpoint para enviar mensajes de prueba"""
        from rest_framework.response import Response
        from dominoapp.connectors.pusher_connector import PushNotificationConnector
        try:
            print("enviando mensaje de prueba")
            data = request.data
            message = data.get('message', 'Hola Mundo!')
            channel = data.get('channel', 'test-channel')
            event = data.get('event', 'hello-event')
            
            pusher_client = PushNotificationConnector.push_notification(
                channel, 
                event, 
                {
                    'message': message,
                    'timestamp': 'Enviado desde Django',
                    'from': 'backend'
                })
            print("mensaje enviado")
            
            
            return Response(data={'status': 'Mensaje enviado', 'channel': channel}, status=200)
        
        except Exception as e:
            return Response(data={'error': str(e)}, status=400)