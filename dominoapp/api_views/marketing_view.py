from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from dominoapp.models import Marketing
from dominoapp.serializers import MarketingSerializer

class MarketingListPagination(PageNumberPagination):
    page_size = 3
    page_size_query_param = "page_size"

class MarketingView(viewsets.ModelViewSet):
    queryset = Marketing.objects.all()
    serializer_class = MarketingSerializer
    pagination_class = MarketingListPagination
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        return super().list(request,*args, **kwargs)