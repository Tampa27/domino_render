from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Sum, OuterRef, Subquery
from dominoapp.utils.pdf_helpers import create_resume_pdf
from dominoapp.models import Player, Status_Transaction

class AdminHelpers:
    
    @staticmethod
    def get_pdf_resume_transaction(modeladmin, request, queryset):
        """
            here we recive a queryset that is a list of the selected transactions
        """  
        queryset = queryset.annotate(
            latest_status_name=Subquery(
                Status_Transaction.objects.filter(status_transaction=OuterRef('pk')
        ).order_by('-created_at').values('status')[:1])
        ).filter(latest_status_name='cp')
        queryset_total = queryset.count()
        queryset_ids = queryset.values_list('id', flat=True)
        
        chunk_size = 10000  # Procesar de 10000 en 10000
        
        queryset = queryset.order_by("time")        
        
        num_days = 0
                
        admin_list = Player.objects.filter(user__is_staff = True).only('id', 'alias')
        
        # Usando values_list para obtener solo lo necesario
        admin_tuples = admin_list.values_list('alias', flat=True).distinct()

        admin_resume = {str(alias): {
            "trans_amount_rl": 0,
            "saldo_amount_rl": 0,
            "total_admin_amount_ext": 0,
            "balance": 0
        } for alias in admin_tuples}
        
        transaction_data = {
                "from_day": queryset.first().time.strftime('%d/%m/%Y'),
                "to_day": queryset.last().time.strftime('%d/%m/%Y'),
                "total_amount_rl": 0,
                "total_amount_ext": 0,
                "total_rl": 0,
                "total_ext": 0,
                "balance_amount": 0,
                "game_amount": 0,
                "mean_rl": "--",
                "mean_ext": "--",
                "mean_amount_rl": "--",
                "mean_amount_ext": "--",
                "admin_resume": admin_resume
        }
        
        for i in range(0, queryset_total, chunk_size):
            queryset_chunk = queryset.filter(id__in = queryset_ids[i:i + chunk_size])
        
            total_amount_rl = queryset_chunk.filter(type ='rl').aggregate(total=Sum('amount'))['total'] or 0
            transaction_data["total_amount_rl"] += total_amount_rl
            
            total_amount_ext = queryset_chunk.filter(type ='ex').aggregate(total=Sum('amount'))['total'] or 0
            transaction_data["total_amount_ext"] += total_amount_ext
            
            total_rl = queryset_chunk.filter(type ='rl').count()
            transaction_data["total_rl"] += total_rl
            
            total_ext = queryset_chunk.filter(type = 'ex').count()
            transaction_data["total_ext"] += total_ext
            
            num_days += (queryset_chunk.last().time - queryset_chunk.first().time).days
            total_amount_loss_in_game = queryset_chunk.filter(type ='gm').exclude(from_user__isnull=True).aggregate(total=Sum('amount'))['total'] or 0
            total_amount_win_in_game = queryset_chunk.filter(type ='gm').exclude(to_user__isnull=True).aggregate(total=Sum('amount'))['total'] or 0
            transaction_data["game_amount"] += round(total_amount_loss_in_game - total_amount_win_in_game, 2)

            for admin in admin_list.iterator():
                trans_amount_rl = queryset_chunk.filter(type ='rl', admin__id = admin.id, paymentmethod='transferencia').aggregate(total=Sum('amount'))['total'] or 0
                transaction_data["admin_resume"][str(admin.alias)]["trans_amount_rl"] += round(trans_amount_rl, 2)
                
                saldo_amount_rl = queryset_chunk.filter(type ='rl', admin__id = admin.id, paymentmethod='saldo').aggregate(total=Sum('amount'))['total'] or 0
                transaction_data["admin_resume"][str(admin.alias)]["saldo_amount_rl"] += round(saldo_amount_rl, 2)
                
                total_admin_amount_ext = queryset_chunk.filter(type ='ex', admin__id = admin.id).aggregate(total=Sum('amount'))['total'] or 0
                transaction_data["admin_resume"][str(admin.alias)]["total_admin_amount_ext"] += round(total_admin_amount_ext, 2)
                
                total_admin_amount_rl = queryset_chunk.filter(type ='rl', admin__id = admin.id).aggregate(total=Sum('amount'))['total'] or 0
                total_admin_amount_ext = queryset_chunk.filter(type ='ex', admin__id = admin.id).aggregate(total=Sum('amount'))['total'] or 0
                transaction_data["admin_resume"][str(admin.alias)]["balance"] += round(total_admin_amount_rl - total_admin_amount_ext, 2)
                
        transaction_data["balance_amount"] = round(transaction_data["total_amount_rl"] - transaction_data["total_amount_ext"], 2)                
        transaction_data["mean_rl"] = str(round(transaction_data['total_rl']/num_days, 1)) if num_days >0 else '--'
        transaction_data["mean_ext"] = str(round(transaction_data['total_ext']/num_days, 1)) if num_days >0 else '--'
        transaction_data["mean_amount_rl"] = str(round(transaction_data['total_amount_rl']/num_days, 2)) if num_days >0 else '--'
        transaction_data["mean_amount_ext"] = str(round(transaction_data['total_amount_ext']/num_days, 2)) if num_days >0 else '--'

        if queryset_total > 0:        
            pdf_out = create_resume_pdf(transaction_data, admin_tuples)

            response = HttpResponse(pdf_out, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="'+ 'model.pdf"' 
            messages.success(request,f"seleccion correcta")
            return response
        
        messages.warning(request, f"No se ha seleccionado ninguna transaccion de recarga o extraccion")
        return
    
        