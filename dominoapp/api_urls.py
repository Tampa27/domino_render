from django.urls import path, include
from rest_framework.routers import DefaultRouter
from dominoapp.api_views import players_view, games_view, payments_view, marketing_view

router = DefaultRouter()
router.register(r"players", players_view.PlayerView)
router.register(r"games", games_view.GameView)
router.register(r"payments", payments_view.PaymentView)
router.register(r"marketing", marketing_view.MarketingView)


urlpatterns = [
    path("", include(router.urls)),
]
