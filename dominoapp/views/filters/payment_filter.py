from rest_framework.filters import SearchFilter
from django.db.models import Subquery, OuterRef
from dominoapp.utils.constants import TransactionStatus, EnumBehavior
from dominoapp.utils.api_http import RequestValidator
from dominoapp.models import Status_Transaction

class PaymentSearchFilter(SearchFilter):
    def filter_queryset(self, request, queryset, view):
        search_term = request.query_params.get('search', '').lower()        

        if RequestValidator.validate_in_array_0(search_term, TransactionStatus.transaction_choices):
            return queryset.annotate(
                    latest_status_name=Subquery(
                        Status_Transaction.objects.filter(status_transaction=OuterRef('pk')
                ).order_by('-created_at').values('status')[:1])
                ).filter(latest_status_name= search_term)

            
        
        # Si no, usar el comportamiento original
        return super().filter_queryset(request, queryset, view)