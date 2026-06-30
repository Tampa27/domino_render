import jwt
import requests, os
from django.core.exceptions import PermissionDenied

class HuaweiTokenVerifier:
    @staticmethod
    def verify(id_token):
        HUAWEI_JWKS_URL = os.getenv('HUAWEI_JWKS_URL')
        HUAWEI_ISSUER = os.getenv('HUAWEI_ISSUER')
        HUAWEI_APP_ID = os.getenv('HUAWEI_APP_ID')
        try:
            # 1. Obtener las llaves públicas actuales de Huawei
            jwks_response = requests.get(HUAWEI_JWKS_URL, timeout=5)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()

            # 2. Leer las cabeceras del token enviado por la app sin verificar aún, 
            # solo para saber qué llave ('kid') se usó para firmarlo
            unverified_header = jwt.get_unverified_header(id_token)
            kid = unverified_header.get("kid")

            # 3. Buscar la llave pública correspondiente en el set de llaves de Huawei
            public_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    # PyJWT puede construir la llave directamente desde los parámetros JWK
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break

            if not public_key:
                raise PermissionDenied("Llave de firma inválida o no encontrada.")

            # 4. Verificar y decodificar el Token por completo
            # Nota: En 'audience' debes poner tu APP ID de Huawei (el número que te da la consola AGC)
            payload = jwt.decode(
                id_token,
                public_key,
                algorithms=["RS256"],
                audience=HUAWEI_APP_ID, # Define esto en tu settings.py
                issuer=HUAWEI_ISSUER
            )

            # El token es 100% real y válido. Devolvemos los datos del jugador extraídos del payload.
            return {
                "uid": payload.get("sub"),          # ID único del usuario en Huawei (openId)
                "email": payload.get("email"),      # Email del usuario
                "name": payload.get("display_name"), # Nombre
                'picture': payload.get('picture', None),
                "success": True
            }

        except jwt.ExpiredSignatureError:
            raise PermissionDenied("El token de Huawei ha expirado.")
        except jwt.InvalidTokenError as e:
            raise PermissionDenied(f"Token de Huawei inválido: {str(e)}")
        except requests.RequestException:
            raise PermissionDenied("No se pudo conectar con los servidores de Huawei para validar el token.")