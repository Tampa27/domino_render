from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from dominoapp.models import Transaction
from dominoapp.api_views.request.payments_request import PaymentRequest
from dominoapp.services.payments_service import PaymentService

class PaymentView(viewsets.GenericViewSet):
    queryset = Transaction.objects.all()
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def recharge(self, request, pk = None):

        is_valid, message, status_response = PaymentRequest.validate_payments(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PaymentService.process_recharge(request)

    @action(detail=False, methods=["post"])
    def extract(self, request, pk = None):

        is_valid, message, status_response = PaymentRequest.validate_payments(request)
        
        if not is_valid:
            return Response(data ={
                "status":'error',
                "message": message
            }, status = status_response)
        
        return PaymentService.process_extract(request)