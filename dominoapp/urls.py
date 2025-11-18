from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt import views as jwt_views
from dominoapp.views import players_view, games_view, payments_view, marketing_view, tournaments_view

router = DefaultRouter()
router.register(r"players", players_view.PlayerView)
router.register(r"games", games_view.GameView)
router.register(r"tournaments", tournaments_view.TournamentsView)
router.register(r"payments", payments_view.PaymentView)
router.register(r"marketing", marketing_view.MarketingView)


urlpatterns = [
    path("", include(router.urls)),
    path("players/login/refresh/", jwt_views.TokenRefreshView.as_view(), name="token_refresh"),
    path("players/login/access/", jwt_views.TokenObtainPairView.as_view(), name="token_obtain_pair"),
]
