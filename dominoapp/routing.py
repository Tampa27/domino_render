from django.urls import re_path
from dominoapp.consumers import games_consumer, lobby_consumer

websocket_urlpatterns = [
    # El id de la mesa se pasa por la URL
    re_path(r'ws/game/(?P<game_id>\w+)/$', games_consumer.GameConsumer.as_asgi()),
    re_path(r'ws/lobby/$', lobby_consumer.LobbyConsumer.as_asgi()),
]