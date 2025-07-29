import os
from rest_framework import status
from rest_framework.response import Response
from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment, LiveEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest, OrdersCaptureRequest
import logging
logger = logging.getLogger('django')

# from .paypal_client import PayPalClient

class PayPalConnector:
    @staticmethod
    def get_client():
        client_id = os.environ.get('PAYPAL_CLIENT_ID', '')
        client_secret = os.environ.get('PAYPAL_SECRET', '')
        try:
            if os.environ.get('PAYPAL_ENVIRONMENT', '') == 'sandbox':
                environment = SandboxEnvironment(
                    client_id=client_id, 
                    client_secret=client_secret
                )
            else:
                environment = LiveEnvironment(
                    client_id=client_id, 
                    client_secret=client_secret
                )
                
            return PayPalHttpClient(environment)
        except Exception as error:
            logger.critical(f"Paypal account is not configured, Error: {str(error)}")
            raise "Paypal account is not configured"

    @staticmethod
    def create_payment(amount, user_email):
        try:
            # Configurar la solicitud de orden
            req = OrdersCreateRequest()
            req.prefer('return=representation')
            
            req.request_body({
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {
                            "currency_code": "USD",
                            "value": str(amount)  # Monto del pago
                        }
                    }
                ],
                "payer":{
                        "email_address": str(user_email)
                    },
                "application_context": {
                    "user_action": "PAY_NOW",
                    "brand_name": "DOMINO_CLUB"
                }
            })
            paypal_client = PayPalConnector.get_client()
            # Ejecutar la solicitud
            response = paypal_client.execute(req)
            
            # Devolver la URL de aprobación al frontend
            approval_url = [link.href for link in response.result.links if link.rel == 'approve'][0]
            
            response_data = {
                'status': 'success',
                'approval_url': approval_url,
                'external_id': response.result.id
            }
            return response_data, None
            
        except Exception as error:
            return None, Response({
                'status': 'error',
                'message': str(error)
            }, status=status.HTTP_409_CONFLICT)

    @staticmethod
    def capture_payment(external_id):
        try:
            req = OrdersCaptureRequest(external_id)
            paypal_client = PayPalConnector.get_client()
            response = paypal_client.execute(req)
            
            # Verificación exhaustiva
            if response.result.status == 'COMPLETED':
                return True  # Pago válido
            else:
                return False  # Estado no esperado

        except Exception as error:
            logger.error(f"Error al completar el pago de paypal, Error: {str(error)}")
            return False    