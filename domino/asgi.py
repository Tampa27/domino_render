"""
ASGI config for domino project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from dominoapp.custom_middleware import JwtAuthMiddleware
import dominoapp.routing # Aquí definirás tus rutas de WS

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JwtAuthMiddleware( # <--- Envolvemos las rutas aquí
        URLRouter(
            dominoapp.routing.websocket_urlpatterns
        )
    ),
})
