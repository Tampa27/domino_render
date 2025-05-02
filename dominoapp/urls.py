from django.urls import path
from . import views

urlpatterns = [
    path('players/', views.PlayersView.as_view(), name='players'),  ## ya esta en player
    path('players/<int:id>/', views.getPlayer,name="player"),       ## ya esta en player
    path('players/<int:id>/update/',views.PlayerView.as_view()),    ## ya esta en player
    path('games/<str:alias>',views.getAllGames,name='games'),
    path('games/<int:game_id>/<str:alias>',views.getGame,name='game'),
    path(r'create/<str:alias>/<str:variant>',views.createGame,name='new game'),
    path(r'join/<str:alias>/<int:game_id>',views.joinGame,name='join game'),
    path(r'start/<int:game_id>',views.startGame,name='start game'),
    path(r'move/<int:game_id>/<str:alias>/<str:tile>/',views.move,name='movement'),
    path(r'cleargames/<str:alias>',views.clearGames,name='clear games'),
    path(r'player/',views.PlayerCreate.as_view(),name='create player'),     ## ya esta en player
    path(r'player/<str:alias>',views.PlayerUpdate.as_view(),name='update player'),  ## este se elimina, ya esta dentro de PlayerView y  solo se usa el id del player
    path(r'game/<str:alias>',views.GameCreate.as_view(),name='create game'),
    path(r'cleanplayers/<str:alias>',views.cleanPlayers,name='clear players'),      ## este se elimina, pq se necesita borrar todos los players
    path(r'exitgame/<int:game_id>/<str:alias>',views.exitGame,name='exit game'),
    path(r'setwinner/<int:game_id>/<int:winner>',views.setWinner,name='set winner'), 
    path(r'setstarter/<int:game_id>/<int:starter>',views.setStarter,name='set starter'),
    path(r'setwinnerstarter/<int:game_id>/<int:winner>/<int:starter>',views.setWinnerStarter,name='set winner starter'),
    path(r'setwinnerstarternext/<int:game_id>/<int:winner>/<int:starter>/<int:next_player>',views.setWinnerStarterNext,name='set winner starter next'), 
    path(r'players/<str:alias>',views.getPlayer,name='get player'),     ## este se elimina, ya esta dentro de PlayerView y solo se usa el id del player
    path(r'setpatner/<int:game_id>/<str:alias>',views.setPatner,name='set patner'),
    path(r'recharge/<str:alias>/<int:coins>',views.rechargeBalance,name='recharge coins'),
    path(r'payment/<str:alias>/<int:coins>',views.payment,name='payment'),
    path(r'bank/',views.getBank,name='get bank'),
    path(r'login/<str:alias>/<str:email>/<str:photo_url>/<str:name>',views.login,name='login'),
    path(r'deletetable/<int:game_id>',views.deleteTable,name='delete table'),
    path(r'deleteinactiveplayers/<str:alias>',views.deleteInactivePlayers,name='delete inactive players'),
    path(r'delete_inactive_tables/<int:days>',views.deleteInactiveTables,name='delete inactive tables'),
]
