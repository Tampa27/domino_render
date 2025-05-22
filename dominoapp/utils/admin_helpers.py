from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Sum
from dominoapp.utils.pdf_helpers import create_resume_pdf

class AdminHelpers:
    
    @staticmethod
    def get_pdf_resume_transaction(modeladmin, request, queryset):
        """
            here we recive a queryset that is a list of the selected transactions
        """  
        queryset_exist = queryset.filter(type__in=['rl', 'ex']).exists()
        if queryset_exist > 0:
            queryset = queryset.filter(type__in=['rl', 'ex']).order_by("time")
            total_amount_rl = queryset.filter(type ='rl').aggregate(total=Sum('amount'))['total'] or 0
            total_amount_ext = queryset.filter(type ='ex').aggregate(total=Sum('amount'))['total'] or 0
            total_rl = queryset.filter(type ='rl').count()
            total_ext = queryset.filter(type = 'ex').count()
            num_days = (queryset.last().time - queryset.first().time).days
            
            transaction_data = {
                "from_day": queryset.first().time.strftime('%d/%m/%Y'),
                "to_day": queryset.last().time.strftime('%d/%m/%Y'),
                "total_rl": str(total_rl),
                "mean_rl": str(total_rl/num_days) if num_days >0 else '--',
                "total_ext": str(total_ext),
                "mean_ext": str(total_ext/num_days) if num_days>0 else "--",
                "total_amount_rl": str(round(total_amount_rl, 2)),
                "total_amount_ext": str(round(total_amount_ext, 2)),
                "mean_amount_rl": str(round(total_amount_rl/num_days, 2)) if num_days>0 else "--",
                "mean_amount_ext": str(round(total_amount_ext/num_days, 2)) if num_days>0 else "--",
                "balance_amount": str(round(total_amount_rl - total_amount_ext, 2))
            }
            pdf_out = create_resume_pdf(transaction_data)

            response = HttpResponse(pdf_out, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="'+ 'model.pdf"' 
            messages.success(request,f"seleccion correcta")
            return response
        else:        
            messages.warning(request, f"No se ha seleccionado ninguna transaccion de recarga o extraccion")
            return
        