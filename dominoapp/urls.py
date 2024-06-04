from django.urls import path
from . import views

urlpatterns = [
    path('players/', views.PlayerView.as_view(), name='players'),
    path('players/<int:id>/', views.PlayerView.as_view()),
    path('players/<int:id>/update/',views.PlayerView.as_view()),
]
