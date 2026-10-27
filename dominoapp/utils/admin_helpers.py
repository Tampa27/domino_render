import logging
from django.contrib import messages
from datetime import datetime
from dominoapp.models import Player
from dominoapp.utils.async_task_helper import enqueue_heavy_task
from dominoapp.tasks import generate_transaction_resume_task

logger = logging.getLogger("django")

class AdminHelpers:
    
    @staticmethod
    def get_pdf_resume_transaction(modeladmin, request, queryset):
        """
            La vista solo valida y encola. Todo el cálculo pesado va al worker.
        """

        # 1) Validación rápida
        queryset_total = queryset.count()
        if queryset_total == 0:
            messages.warning(request, "No se ha seleccionado ninguna transacción.")
            return

        # 2) Extraer solo los filtros que nos interesan de request.GET
        filters = {}

        # list_filter estándar: ?game=<id>&type=rl
        for key in ("game", "type"):
            val = request.GET.get(key)
            if val:
                filters[key] = val
        
        # AdminFilter: ?admin=<player_id>
        admin_id = request.GET.get("admin")
        if admin_id:
            filters["admin_id"] = admin_id

        # FromTimeFilter: ?from_date=DD/MM/YYYY → time__date__gte
        from_date = request.GET.get("from_date")
        if from_date:
            try:
                filters["time__date__gte"] = datetime.strptime(from_date, "%d/%m/%Y").date().isoformat()
            except ValueError:
                logger.warning(f"from_date inválido: {from_date}")

        # ToTimeFilter: ?to_date=DD/MM/YYYY → time__date__lt
        to_date = request.GET.get("to_date")
        if to_date:
            try:
                filters["time__date__lt"] = datetime.strptime(to_date, "%d/%m/%Y").date().isoformat()
            except ValueError:
                logger.warning(f"to_date inválido: {to_date}")

        # StatusFilter: ?status=cp → se aplica como latest_status_name=...
        status = request.GET.get("status")
        if status:
            filters["status"] = status

        # search: ?q=texto
        search = request.GET.get("q")
        if search:
            filters["search"] = search.strip()

        # 3) Admin aliases (rápido)
        admin_tuples = list(
            Player.objects.filter(user__is_staff=True)
            .values_list('alias', flat=True).distinct()
        )
        
        to_email = ["mcr.sibucan@gmail.com"]

        enqueue_heavy_task(
            generate_transaction_resume_task,
            filters,
            admin_tuples,
            to_email,
        )

        messages.success(
            request,
            f"El resumen de {queryset_total} transacciones se está generando "
            f"y se enviará a {', '.join(to_email)} en breve."
        )
        return
