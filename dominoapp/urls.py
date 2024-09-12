from django.urls import path
from . import views

urlpatterns = [
    path('players/', views.PlayersView.as_view(), name='players'),
    path('players/<int:id>/', views.PlayerView.as_view(),name="player"),
    path('players/<int:id>/update/',views.PlayerView.as_view()),
    path('games/',views.getAllGames,name='games'),
    path('games/<int:game_id>',views.getGame,name='game'),
    path(r'create/<str:alias>/<str:variant>',views.createGame,name='new game'),
    path(r'join/<str:alias>/<int:game_id>',views.joinGame,name='join game'),
    path(r'start/<int:game_id>',views.startGame,name='start game'),
    path(r'move/<int:game_id>/<str:alias>/<str:tile>/',views.move,name='movement'),
    path(r'cleargames/',views.clearGames,name='clear games'),
    path(r'player/',views.PlayerCreate.as_view(),name='create player'),
    path(r'player/<str:alias>',views.PlayerUpdate.as_view(),name='update player'),
    path(r'game/<str:alias>',views.GameCreate.as_view(),name='create game'),
    path(r'cleanplayers/',views.cleanPlayers,name='clear players'),
    path(r'exitgame/<int:game_id>/<str:alias>',views.exitGame,name='exit game'),
    path(r'setwinner/<int:game_id>/<int:winner>',views.setWinner,name='set winner'),
    path(r'setstarter/<int:game_id>/<int:starter>',views.setStarter,name='set starter'),
    path(r'setwinnerstarter/<int:game_id>/<int:winner>/<int:starter>',views.setWinnerStarter,name='set winner starter'),
    path(r'setwinnerstarternext/<int:game_id>/<int:winner>/<int:starter>/<int:next_player>',views.setWinnerStarterNext,name='set winner starter next'),
    path(r'players/<str:alias>',views.getPlayer,name='get player'),
    path(r'start1/<int:game_id>',views.startGame1,name='start game 1'),
]
