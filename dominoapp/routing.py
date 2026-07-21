from django.urls import path
from dominoapp.consumers import games_consumer, lobby_consumer, chat_consumer

websocket_urlpatterns = [
    # El id de la mesa se pasa por la URL
    path('ws/game/<str:game_id>/', games_consumer.GameConsumer.as_asgi()),
    path('ws/lobby/', lobby_consumer.LobbyConsumer.as_asgi()),
    path('ws/chat/<uuid:chat_id>/', chat_consumer.ChatConsumer.as_asgi()),

]