from django.contrib import messages
from django.db.models import Sum, Count, Q, OuterRef, Subquery, FloatField
from django.db.models.functions import Coalesce, TruncDate
from datetime import timedelta
from dominoapp.models import Player, Status_Transaction
from dominoapp.utils.async_task_helper import enqueue_heavy_task
from dominoapp.tasks import generate_transaction_pdf_and_email

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
        ).filter(latest_status_name='cp').exclude(type__in =['pro'])
        queryset_total = queryset.count()
        if queryset_total == 0:
            messages.warning(request, f"No se ha seleccionado ninguna transaccion de recarga o extraccion")
            return


        # --- Rango de fechas (2 queries rápidas, no cargan filas) ---
        first = queryset.order_by('time').values('time').first()
        last  = queryset.order_by('-time').values('time').first()
        first_time, last_time = first['time'], last['time']
        diference_day = (last_time - first_time).days
        num_days = diference_day if diference_day > 0 else 1

        # --- Admin list ---
        admin_list = Player.objects.filter(user__is_staff=True).only('id', 'alias')
        admin_tuples = list(admin_list.values_list('alias', flat=True).distinct())

        admin_resume = {str(a): {"trans_amount_rl": 0, "saldo_amount_rl": 0, "trans_num": 0,
                                "total_admin_amount_ext": 0, "ext_num": 0, "balance": 0}
                        for a in admin_tuples}

        transaction_data = {
            "from_day": first_time.strftime('%d/%m/%Y'),
            "to_day":   last_time.strftime('%d/%m/%Y'),
            "total_amount_rl": 0, "total_amount_rl_USD": 0, "total_amount_ext": 0,
            "total_amount_reward": 0, "total_rl": 0, "total_rl_USD": 0,
            "total_pro_mov": 0, "total_ext": 0, "total_reward": 0,
            "balance_amount": 0, "game_amount": 0, "transfer_amount": 0,
            "mean_rl": "--", "mean_ext": "--", "mean_amount_rl": "--", "mean_amount_ext": "--",
            "admin_resume": admin_resume,
            "graph": {"days": 0, "reload": [], "extraction": [], "balance": []},
            "promo_by_country": {},
        }

        amount_expr = Coalesce('transaction_payment__amount', 'amount', output_field=FloatField())

        # ===== 1) Agregados globales: UNA query =====
        agg = queryset.aggregate(
            total_amount_rl=Sum(amount_expr, filter=Q(type='rl') & ~Q(paymentmethod__in=["paypal","zelle","google"])),
            total_amount_rl_USD=Sum(amount_expr, filter=Q(type='rl', paymentmethod__in=["paypal","zelle","google"])),
            total_amount_ext=Sum(amount_expr, filter=Q(type__in=['ex','rw'])),
            total_amount_reward=Sum(amount_expr, filter=Q(type='rw')),
            total_rl=Count('id', filter=Q(type='rl') & ~Q(paymentmethod__in=["paypal","zelle","google"])),
            total_rl_USD=Count('id', filter=Q(type='rl', paymentmethod__in=["paypal","zelle","google"])),
            total_pro_mov=Count('id', filter=Q(type='pro_mov')),
            total_ext=Count('id', filter=Q(type__in=['ex','rw'])),
            total_reward=Count('id', filter=Q(type='rw')),
            game_loss=Sum('amount', filter=Q(type='gm') & Q(from_user__isnull=False)),
            game_win=Sum('amount', filter=Q(type='gm') & Q(to_user__isnull=False)),
            transfer_out=Sum('amount', filter=Q(type='tr') & Q(from_user__isnull=False)),
            transfer_in=Sum('amount', filter=Q(type='tr') & Q(to_user__isnull=False)),
        )

        for k in ['total_amount_rl','total_amount_rl_USD','total_amount_ext','total_amount_reward',
                'total_rl','total_rl_USD','total_pro_mov','total_ext','total_reward']:
            transaction_data[k] = agg[k] or 0
        
        transaction_data["game_amount"]     = round((agg['game_loss'] or 0) - (agg['game_win'] or 0), 2)
        transaction_data["transfer_amount"] = round((agg['transfer_out'] or 0) - (agg['transfer_in'] or 0), 2)

        transaction_data["balance_amount"]  = round(transaction_data["total_amount_rl"] - transaction_data["total_amount_ext"], 2)
        transaction_data["mean_rl"]         = str(round(transaction_data['total_rl'] / num_days, 1)) if num_days > 0 else '--'
        transaction_data["mean_ext"]        = str(round(transaction_data['total_ext'] / num_days, 1)) if num_days > 0 else '--'
        transaction_data["mean_amount_rl"]  = str(round(transaction_data['total_amount_rl'] / num_days, 2)) if num_days > 0 else '--'
        transaction_data["mean_amount_ext"] = str(round(transaction_data['total_amount_ext'] / num_days, 2)) if num_days > 0 else '--'

        # ===== 2) Admin resume: UNA query agrupada =====
        admin_agg = (
            queryset.filter(admin__isnull=False)
            .values('admin__alias')
            .annotate(
                trans_num=Count('id', filter=Q(type='rl') & ~Q(paymentmethod__in=["paypal","zelle","google"])),
                trans_amount_rl=Sum(amount_expr, filter=Q(type='rl', paymentmethod='transferencia')),
                saldo_amount_rl=Sum(amount_expr, filter=Q(type='rl', paymentmethod='saldo')),
                ext_num=Count('id', filter=Q(type='ex')),
                total_admin_amount_ext=Sum(amount_expr, filter=Q(type='ex')),
                total_admin_amount_rl=Sum(amount_expr, filter=Q(type='rl') & ~Q(paymentmethod__in=["paypal","zelle","google"])),
            )
        )
        for row in admin_agg:
            alias = row['admin__alias']
            if alias not in transaction_data["admin_resume"]:
                continue
            transaction_data["admin_resume"][alias] = {
                "trans_amount_rl": round(row['trans_amount_rl'] or 0, 2),
                "saldo_amount_rl": round(row['saldo_amount_rl'] or 0, 2),
                "trans_num": row['trans_num'] or 0,
                "total_admin_amount_ext": round(row['total_admin_amount_ext'] or 0, 2),
                "ext_num": row['ext_num'] or 0,
                "balance": round((row['total_admin_amount_rl'] or 0) - (row['total_admin_amount_ext'] or 0), 2),
            }

        # ===== 3) Gráfico: UNA query agrupada por día =====
        daily = (
            queryset.annotate(day=TruncDate('time')).values('day')
            .annotate(
                reload=Sum(amount_expr, filter=Q(type='rl') & ~Q(paymentmethod__in=["paypal","zelle","google"])),
                extraction=Sum(amount_expr, filter=Q(type__in=['ex','rw'])),
            ).order_by('day')
        )
        daily_map = {row['day']: row for row in daily}
        first_day = first_time.date()
        n_days_total = diference_day + 1 if diference_day > 0 else 1
        transaction_data["graph"]["days"] = list(range(1, n_days_total + 1))
        for offset in range(n_days_total):
            d = first_day + timedelta(days=offset)
            row = daily_map.get(d)
            r = float(row['reload'])     if row and row['reload']     else 0
            e = float(row['extraction']) if row and row['extraction'] else 0
            transaction_data["graph"]["reload"].append(r)
            transaction_data["graph"]["extraction"].append(e)
            transaction_data["graph"]["balance"].append(r - e)

        # ===== 4) Promociones por país: UNA query agrupada =====
        promotions_by_country = (
            queryset.filter(type='pro_mov').values('to_user__country')
            .annotate(total=Count('id')).order_by('-total')
        )
        for row in promotions_by_country:
            c = row['to_user__country']
            key = c.strip().upper() if c and c.strip() else 'OTHER'
            transaction_data["promo_by_country"][key] = transaction_data["promo_by_country"].get(key, 0) + row['total']

        to_email = ["mcr.sibucan@gmail.com"]
        enqueue_heavy_task(
            generate_transaction_pdf_and_email,
            transaction_data,
            admin_tuples,
            to_email,
        )

        messages.success(
            request,
            f"El resumen se está generando y se enviará a {', '.join(to_email)} en breve."
        )
        return  # No devolvemos HttpResponse → el admin recarga la lista con el mensaje

        