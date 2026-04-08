from django.urls import re_path
from dominoapp.utils import websocket_consumers

websocket_urlpatterns = [
    # El id de la mesa se pasa por la URL
    re_path(r'ws/game/(?P<game_id>\w+)/$', websocket_consumers.GameConsumer.as_asgi()),
]