from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Sum
from dominoapp.utils.pdf_helpers import create_resume_pdf
from dominoapp.models import Player

class AdminHelpers:
    
    @staticmethod
    def get_pdf_resume_transaction(modeladmin, request, queryset):
        """
            here we recive a queryset that is a list of the selected transactions
        """  
        queryset_exist = queryset.count()
        if queryset_exist > 0:
            queryset = queryset.order_by("time")
            total_amount_rl = queryset.filter(type ='rl').aggregate(total=Sum('amount'))['total'] or 0
            total_amount_ext = queryset.filter(type ='ex').aggregate(total=Sum('amount'))['total'] or 0
            total_rl = queryset.filter(type ='rl').count()
            total_ext = queryset.filter(type = 'ex').count()
            num_days = (queryset.last().time - queryset.first().time).days
            total_amount_loss_in_game = queryset.filter(type ='gm').exclude(from_user__isnull=True).aggregate(total=Sum('amount'))['total'] or 0
            total_amount_win_in_game = queryset.filter(type ='gm').exclude(to_user__isnull=True).aggregate(total=Sum('amount'))['total'] or 0

            admin_list = Player.objects.filter(user__is_superuser = True).only('id', 'alias')
            
            admin_resume = []
            for admin in admin_list.iterator():
                total_admin_amount_rl = queryset.filter(type ='rl', admin__id = admin.id).aggregate(total=Sum('amount'))['total'] or 0
                trans_amount_rl = queryset.filter(type ='rl', admin__id = admin.id, paymentmethod='transferencia').aggregate(total=Sum('amount'))['total'] or 0
                saldo_amount_rl = queryset.filter(type ='rl', admin__id = admin.id, paymentmethod='saldo').aggregate(total=Sum('amount'))['total'] or 0
                total_admin_amount_ext = queryset.filter(type ='ex', admin__id = admin.id).aggregate(total=Sum('amount'))['total'] or 0

                admin_resume.append(
                    {
                        "alias": str(admin.alias),
                        "trans_amount_rl": str(round(trans_amount_rl, 2)),
                        "saldo_amount_rl": str(round(saldo_amount_rl, 2)),
                        "total_admin_amount_ext": str(round(total_admin_amount_ext, 2)),
                        "balance": str(round(total_admin_amount_rl - total_admin_amount_ext, 2)),
                    }
                )


            transaction_data = {
                "from_day": queryset.first().time.strftime('%d/%m/%Y'),
                "to_day": queryset.last().time.strftime('%d/%m/%Y'),
                "total_rl": str(total_rl),
                "mean_rl": str(round(total_rl/num_days, 1)) if num_days >0 else '--',
                "total_ext": str(total_ext),
                "mean_ext": str(round(total_ext/num_days, 1)) if num_days>0 else "--",
                "total_amount_rl": str(round(total_amount_rl, 2)),
                "total_amount_ext": str(round(total_amount_ext, 2)),
                "mean_amount_rl": str(round(total_amount_rl/num_days, 2)) if num_days>0 else "--",
                "mean_amount_ext": str(round(total_amount_ext/num_days, 2)) if num_days>0 else "--",
                "balance_amount": str(round(total_amount_rl - total_amount_ext, 2)),
                "game_amount": str(round(total_amount_loss_in_game - total_amount_win_in_game, 2)),
                "admin_resume": admin_resume
            }
            pdf_out = create_resume_pdf(transaction_data)

            response = HttpResponse(pdf_out, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="'+ 'model.pdf"' 
            messages.success(request,f"seleccion correcta")
            return response
        else:        
            messages.warning(request, f"No se ha seleccionado ninguna transaccion de recarga o extraccion")
            return
    
        