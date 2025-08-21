"""
URL configuration for domino project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from dominoapp.views.players_view import PlayerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('v2/api/',include('dominoapp.urls')),
     # URLs de documentación
    path('v2/api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Opcional: UI de Swagger
    path('v2/api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Opcional: UI de Redoc
    path('v2/api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path("refer/", PlayerView.as_view({'get': 'refer_register'}), name="share_refer")
]
