"""
ASGI config for domino project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application

# PRIMERO configuramos el entorno
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
# SEGUNDO inicializamos Django
django.setup()

# TERCERO obtenemos la app HTTP (esto debe ir antes de importar routing o middleware)
django_asgi_app = get_asgi_application()

# CUARTO: Ahora sí, importaciones que dependen de Django/Apps
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
