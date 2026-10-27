from celery import shared_task
import logging, os
from dominoapp.models import DominoGame, Tournament, Player, SummaryPlayer, Bank, Notification, Transaction, \
    Status_Transaction
from django.db import transaction
from django.db.models import F, Sum, Count, Q, OuterRef, Subquery, FloatField
from django.db.models.functions import Coalesce, TruncDate
from django.utils.timezone import now
from datetime import datetime, date, timedelta
from dominoapp.utils.transactions import create_game_transactions, create_transactions
from dominoapp.utils.players_tools import get_summary_model
from dominoapp.utils.move_register_utils import movement_register
from dominoapp.utils.checktables import procesar_logica_de_mesa, automatic_tournament
from dominoapp.utils.fcm_message import FCMNOTIFICATION
from dominoapp.utils.whatsapp_help import get_whatsapp_tournament_notify
from dominoapp.utils.pdf_helpers import create_resume_pdf
from dominoapp.connectors.email_connector import EmailConnector
logger = logging.getLogger('django')

@shared_task(name="task_maestra_domino", ignore_result=True)
def task_maestra_domino():
    """
    Se ejecuta cada 7s. Identifica mesas activas y lanza procesos individuales.
    """
    # Filtramos mesas que no estén vacías y tengan estados que requieran atención
    # Estados: 'ru' (jugando), 'fg'/'fi' (terminado), 'wt'/'ready' (esperando)
    mesas_activas = DominoGame.objects.filter(
        player1__isnull=False,
        status__in=['ru', 'fg', 'fi', 'wt', 'ready']
    ).values_list('id', flat=True)

    for game_id in mesas_activas:
        # Lanzamos la subtarea para cada mesa de forma asíncrona
        procesar_mesa_individual.delay(game_id)
    
    # También lanzamos la lógica de torneos
    tournaments_active = Tournament.objects.filter(active=True).values_list('id', flat=True)
    for tournament_id in tournaments_active:
        task_logica_torneos.delay(tournament_id)

@shared_task(name="procesar_mesa_individual", ignore_result=True)
def procesar_mesa_individual(game_id):
    """
    Procesa toda la lógica (movimientos, reinicios, expulsiones) de una sola mesa.
    """
    procesar_logica_de_mesa(game_id)

@shared_task(name="task_logica_torneos", ignore_result=True)
def task_logica_torneos(tournament_id):
    """Procesa toda la lógica de los torneos (reinicios, expulsiones, notificaciones)."""
    automatic_tournament(tournament_id)

@shared_task(name="async_update_summarys", ignore_result=True)
def async_update_summarys(game_id: int= None, player_data_list: list = None, bank_update_data: dict=None, move_data: dict = None):
    """
    Procesa actualizaciones masivas de estadísticas, transacciones y registros de movimientos.
    """
    # 1. Actualizar Banco
    if bank_update_data:
        try:
            with transaction.atomic():
                firts_bank = Bank.objects.first()
                update_kwargs = {k: F(k) + v for k, v in bank_update_data.items() if v != 0}
                if update_kwargs:
                    Bank.objects.filter(id=firts_bank.id).update(**update_kwargs)
        except Exception as e:
            logger.error(f"Error actualizando Banco en proceso asincrono: {e}")

    # 2. Registrar el Movimiento (Movido desde game_tools.py)
    move_register = None
    if move_data:
        try:
            move_register = movement_register(**move_data)
        except Exception as e:
            logger.error(f"Error creando MoveRegister en proceso asincrono: {e}")

    if not player_data_list:
        return

    # 3. Iterar sobre jugadores
    for data in player_data_list:
        try:
            with transaction.atomic():
                player = Player.objects.get(id=data['id'])
                
                # Actualizar Summary (Estadísticas acumuladas)
                if data.get('summary_fields'):
                    summary = get_summary_model(player)
                    summary_updates = {k: F(k) + v for k, v in data['summary_fields'].items()}
                    SummaryPlayer.objects.filter(id=summary.id).update(**summary_updates)

                # Crear Transacción
                trans = data.get('transaction')
                if trans:
                    try:
                        game = DominoGame.objects.get(id=game_id) if game_id else None
                        create_game_transactions(
                            game= game,
                            to_user=player if trans.get('to_user') else None,
                            from_user=player if trans.get('from_user') else None,
                            amount=trans['amount'],
                            status="cp",
                            descriptions=trans['description'],
                            move_register=move_register
                        )
                    except:
                        create_transactions(
                            to_user=player if trans.get('to_user') else None,
                            from_user=player if trans.get('from_user') else None,
                            amount=trans['amount'],
                            status="cp",
                            type="gm",
                            descriptions=trans['description']
                        )
        except Exception as e:
            logger.error(f"Error procesando jugador {data.get('id')} en proceso asincrono: {e}")

@shared_task(name="async_update_player_presence", ignore_result=True)
def async_update_player_presence(player_data: dict):
    """
    Procesa actualizaciones de presencia de jugadores.
    """
    player_id = player_data.get('id')
    if not player_id:
        logger.error("Error: player_data debe contener 'id'.")
        return

    try:
        Player.objects.filter(id=player_id).update(**player_data)

    except Exception as e:
        logger.error(f"Error actualizando presencia del Jugador en proceso asincrono: {e}")

    return


@shared_task(name="async_send_fcm_message", ignore_result=True)
def async_send_fcm_message(users_id: list[int], title: str, message: str):
    """
    Procesa el envío de mensajes FCM a usuarios.
    """
    FCMNOTIFICATION.send_fcm_message_by_users_list(
        users = users_id,
        title = title,
        body = message
    )

    return

@shared_task(name="async_send_global_fcm_message", ignore_result=True)
def async_send_global_fcm_message(title: str, message: str):
    """
    Procesa el envío de mensajes FCM a todos los usuarios.
    """
    FCMNOTIFICATION.send_fcm_global_message(
        title = title,
        body = message
    )

    return

@shared_task(name="", ignore_result=True)
def async_save_place_tournament_notification(place_1_notification: dict, place_2_notification: dict, place_3_notification: dict):
    """
    Procesa las notificaciones de los lugares en un torneo.
    """ 
    admin_phone = os.environ.get('ADMIN_PHONE', None)
    if not admin_phone:
        admin_phone = "+5352459418"
        logger.critical("ADMIN_PHONE no está configurado en las variables de entorno.")

    if not place_1_notification:
        logger.error("Error: place_1_notification debe ser un diccionario.")
        return
    
    users_1er_place = place_1_notification.get('users_id')
    if not users_1er_place:
        logger.error("Error: place_1_notification debe contener 'users_id'.")
        return
    
    message_1er_place = place_1_notification.get("message")
    if message_1er_place:
        FCMNOTIFICATION.send_fcm_message_by_users_list(
            users = users_1er_place,
            title = place_1_notification.get('title'),
            body = message_1er_place
        )
    
    try:
        players_1er_place = Player.objects.filter(user__id__in = users_1er_place)
        for player in players_1er_place:            
            whatsapp_url = get_whatsapp_tournament_notify(
                player=player,
                player_phone=admin_phone,
                message=message_1er_place
            )

            Notification.objects.create(
                player=player,
                title=place_1_notification.get('title'),
                message=f"{message_1er_place}. Tienes 10 días para reclamar tu premio.",
                whatsapp_url = whatsapp_url
            )
    except Exception as error:
        logger.error(f"Error al crear las notificaciones del Torneo para el 1er lugar, error: {error}")

    if place_2_notification:
        users_2nd_place = place_2_notification.get('users_id')
        if users_2nd_place:
            message_2nd_place = place_2_notification.get("message")
            if message_2nd_place:
                FCMNOTIFICATION.send_fcm_message_by_users_list(
                    users = users_2nd_place,
                    title = place_2_notification.get('title'),
                    body = message_2nd_place
                )
            
            try:
                players_2nd_place = Player.objects.filter(user__id__in = users_2nd_place)
                for player in players_2nd_place:
                    whatsapp_url = get_whatsapp_tournament_notify(
                        player=player,
                        player_phone=admin_phone,
                        message=message_2nd_place
                    )

                    Notification.objects.create(
                        player= player,
                        title= place_2_notification.get('title'),
                        message=f"{message_2nd_place}. Tienes 10 días para reclamar tu premio.",
                        whatsapp_url = whatsapp_url
                    )
            except Exception as error:
                logger.error(f"Error al crear las notificaciones del Torneo para el 2do lugar, error: {error}")

    if place_3_notification:
        users_3th_place = place_3_notification.get('users_id')
        if users_3th_place:
            message_3th_place = place_3_notification.get("message")
            if message_3th_place:
                FCMNOTIFICATION.send_fcm_message_by_users_list(
                    users = users_3th_place,
                    title = place_3_notification.get('title'),
                    body = message_3th_place
                )
            
            try:
                players_3th_place = Player.objects.filter(user__id__in = users_3th_place)
                for player in players_3th_place:
                    whatsapp_url = get_whatsapp_tournament_notify(
                        player=player,
                        player_phone=admin_phone,
                        message=message_3th_place
                    )

                    Notification.objects.create(
                        player= player,
                        title= place_3_notification.get('title'),
                        message=f"{message_3th_place}. Tienes 10 días para reclamar tu premio.",
                        whatsapp_url = whatsapp_url
                    )
            except Exception as error:
                logger.error(f"Error al crear las notificaciones del Torneo para el 3er lugar, error: {error}")

    return

##### Admin Task #######################

@shared_task(bind=True, max_retries=2, default_retry_delay=30, ignore_result=True)
def generate_transaction_pdf_and_email(
    self,
    transaction_data: dict,
    admin_tuples: list,
    to_email: list[str],
):
    """
    Genera el PDF de resumen de transacciones y lo envía por correo.
    `transaction_data` y `admin_tuples` ya vienen calculados desde la vista.
    """
    try:
        # 1) Generar PDF (operación pesada)
        pdf_bytes = create_resume_pdf(transaction_data, admin_tuples)

        # 2) Preparar nombre y asunto
        filename = f"resumen_transacciones_{now().strftime('%Y%m%d_%H%M%S')}.pdf"
        subject = "Resumen de transacciones - Dominó Club"

        html_message = (
            f"<p>Adjunto encontrará el resumen de transacciones "
            f"generado el {now().strftime('%d/%m/%Y %H:%M')}.</p>"
            f"<p>Rango: {transaction_data['from_day']} — {transaction_data['to_day']}</p>"
        )

        # 3) Enviar correo con adjunto
        ok = EmailConnector.django_send_email_with_attachment(
            to_email=to_email,
            subject=subject,
            attachment=pdf_bytes,
            filename=filename,
            from_email=EmailConnector.admin_email,
            text="Adjunto encontrará el resumen de transacciones.",
            html=html_message,
        )

        if not ok:
            raise Exception("EmailConnector devolvió False al enviar el correo.")

        logger.info(f"PDF de transacciones enviado a {to_email}")
        return {"status": "ok", "filename": filename}

    except Exception as exc:
        logger.error(f"Error generando/enviando PDF de transacciones: {exc}")
        raise self.retry(exc=exc)

def _build_transaction_queryset(filters: dict):
    """
    Reconstruye el queryset aplicando los mismos filtros que el admin:
    - game, type, admin_id: Exact
    - time__date__gte, time__date__lt: DateGte / DateLt
    - status: anota latest_status_name y filtra por él
    - search: Q OR sobre from_user__alias, to_user__alias, from_user__email, to_user__email
    """
    qs = Transaction.objects.all()

    # Filtros Exact simples
    if filters.get("game"):
        qs = qs.filter(game_id=filters["game"])
    if filters.get("type"):
        qs = qs.filter(type=filters["type"])
    if filters.get("admin_id"):
        qs = qs.filter(admin_id=filters["admin_id"])

    # Rango de fechas (deserializar ISO strings a date)
    if filters.get("time__date__gte"):
        d = date.fromisoformat(filters["time__date__gte"])
        qs = qs.filter(time__date__gte=d)
    if filters.get("time__date__lt"):
        d = date.fromisoformat(filters["time__date__lt"])
        qs = qs.filter(time__date__lt=d)

    # Search: replicar search_fields del TransactionAdmin
    if filters.get("search"):
        s = filters["search"]
        qs = qs.filter(
            Q(from_user__alias__icontains=s) |
            Q(to_user__alias__icontains=s) |
            Q(from_user__email__icontains=s) |
            Q(to_user__email__icontains=s)
        )

    # Status: anotar y filtrar (igual que StatusFilter del admin)
    qs = qs.annotate(
        latest_status_name=Subquery(
            Status_Transaction.objects
            .filter(status_transaction=OuterRef('pk'))
            .order_by('-created_at')
            .values('status')[:1]
        )
    )
    # Si no se especifica status, forzar 'cp' (comportamiento original)
    if filters.get("status"):
        qs = qs.filter(latest_status_name=filters["status"])
    else:
        qs = qs.filter(latest_status_name="cp")

    # Excluir type='pro' (igual que tu vista original)
    qs = qs.exclude(type__in=['pro'])

    return qs

@shared_task(bind=True, max_retries=2, default_retry_delay=30, ignore_result=True,soft_time_limit=300, time_limit=360)
def generate_transaction_resume_task(self, filters: dict, admin_tuples: list, to_email: list[str]):
    """
    Reconstruye el queryset desde `filters`, calcula agregados, genera PDF y envía correo.
    Se ejecuta en el worker (sin límite de 30s de Heroku).
    """
    try:
        # ===== 1) Reconstruir queryset =====
        queryset = _build_transaction_queryset(filters)
        queryset_total = queryset.count()
        if queryset_total == 0:
            logger.error(f"generate_transaction_resume_task: 0 transacciones con filters={filters}")
            return

        # ===== 2) Rango de fechas =====
        first = queryset.order_by('time').values('time').first()
        last = queryset.order_by('-time').values('time').first()
        first_time, last_time = first['time'], last['time']
        diference_day = (last_time - first_time).days
        num_days = diference_day if diference_day > 0 else 1

        # ===== 3) Admin resume inicial =====
        admin_resume = {
            str(a): {"trans_amount_rl": 0, "saldo_amount_rl": 0, "trans_num": 0,
                     "total_admin_amount_ext": 0, "ext_num": 0, "balance": 0}
            for a in admin_tuples
        }

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

        # ===== 4) Agregados globales =====
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

        # ===== 5) Admin resume agrupado =====
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

        # ===== 6) Gráfico por día =====
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

        # ===== 7) Promociones por país =====
        promotions_by_country = (
            queryset.filter(type='pro_mov').values('to_user__country')
            .annotate(total=Count('id')).order_by('-total')
        )
        for row in promotions_by_country:
            c = row['to_user__country']
            key = c.strip().upper() if c and c.strip() else 'OTHER'
            transaction_data["promo_by_country"][key] = (
                transaction_data["promo_by_country"].get(key, 0) + row['total']
            )

        # ===== 8) PDF + email =====
        pdf_bytes = create_resume_pdf(transaction_data, admin_tuples)

        filename = f"resumen_transacciones_{now().strftime('%Y%m%d_%H%M%S')}.pdf"
        subject = "Resumen de transacciones - Dominó Club"
        html_message = (
            f"<p>Adjunto encontrará el resumen de transacciones "
            f"generado el {now().strftime('%d/%m/%Y %H:%M')}.</p>"
            f"<p>Rango: {transaction_data['from_day']} — {transaction_data['to_day']}</p>"
            f"<p>Total transacciones: {queryset_total}</p>"
        )

        ok = EmailConnector.django_send_email_with_attachment(
            to_email=to_email,
            subject=subject,
            attachment=pdf_bytes,
            filename=filename,
            from_email=EmailConnector.admin_email,
            text="Adjunto encontrará el resumen de transacciones.",
            html=html_message,
        )
        if not ok:
            raise Exception("EmailConnector devolvió False al enviar el correo.")

        logger.info(f"Resumen de transacciones ({queryset_total}) enviado a {to_email}")

    except Exception as exc:
        logger.error(f"Error en generate_transaction_resume_task: {exc}", exc_info=True)
        if self.request.retries >= self.max_retries:
            logger.critical(f"generate_transaction_resume_task FALLÓ definitivamente: {exc}")
            return
        raise self.retry(exc=exc)