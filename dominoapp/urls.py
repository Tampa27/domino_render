from django.urls import path
from . import views

urlpatterns = [
    path('players/', views.PlayerView.as_view(), name='players')
]
