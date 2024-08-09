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

]
