"""General web socket middlewares
"""

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except:
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Los subprotocolos vienen en una lista dentro del scope
        subprotocols = scope.get("subprotocols", [])
        user = AnonymousUser()

        # Buscamos el token. Por convención se suele enviar como:
        # ['access_token', 'TU_JWT_TOKEN']
        if "access_token" in subprotocols:
            try:
                token_index = subprotocols.index("access_token") + 1
                token_key = subprotocols[token_index]
                
                # Validar el token
                token = AccessToken(token_key)
                user = await get_user(token["user_id"])
            except Exception:
                user = AnonymousUser()

        scope['user'] = user
        return await self.inner(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)
