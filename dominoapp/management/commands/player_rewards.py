import os, logging
from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from django.db import transaction
from django.db.models import Q, F, Value, Exists, OuterRef, Sum, IntegerField, Subquery
from django.db.models.functions import Coalesce
from dateutil.relativedelta import relativedelta
from dominoapp.models import PlayerReward, SummaryPlayer, Notification, Player, BlockPlayer
from dominoapp.utils.transactions import create_reward_transactions
from dominoapp.utils.fcm_message import FCMNOTIFICATION
from dominoapp.utils.whatsapp_help import get_whatsapp_reward_text

logger = logging.getLogger("django")

# mapa explícito
REWARD_TYPE_LABELS = {
    "match_wins": "partidas ganadas",
    "pass_player": "jugadores pasados",
    "earned_coins": "monedas ganadas",
    "play_99_game": "juegos del 9|9 jugados",
    "play_66_game": "juegos del 6|6 jugados",
    "play_in_pairs": "juegos en parejas jugados",
    "play_in_single": "juegos en solitario jugados",
    "play_by_points": "juegos por puntos jugados",
    "play_without_points": "juegos sin puntos jugados",
}

def _get_admin_phone():
    """
    telefono de administracion
    """
    for var in ("ADMIN_PHONE", "ADMIN_PHONE_1"):
        value = os.environ.get(var)
        if value:
            return value
    logger.critical(
        "ADMIN_PHONE/ADMIN_PHONE_1 no configurados; usando número por defecto."
    )
    return "+5352459418"

def _month_start(reference):
    """primer día del mes anterior"""
    if relativedelta is not None:
        return reference - relativedelta(months=1)
    # Fallback manual: primer día del mes anterior.
    if reference.month == 1:
        return reference.replace(year=reference.year - 1, month=12, day=1)
    return reference.replace(month=reference.month - 1, day=1)

class Command(BaseCommand):
    help = "Entrega los premios semanales/mensuales a los jugadores destacados."

    def handle(self, *args, **options):
        time_now = now().replace(hour=0, minute=0, second=0, microsecond=0)
        rewards = PlayerReward.objects.filter(
            Q(date_of_week = time_now.weekday())|Q(date_of_month = time_now.day)
        )
        players_list = Player.objects.all().exclude(
            Exists(BlockPlayer.objects.filter(
                    player_blocked__id = OuterRef('id')
                )
            )
        )
        admin_phone = _get_admin_phone()

        for reward in rewards:
            period = None  # "semana" | "mes"
            
            if reward.date_of_week is not None:
                period = "semana"
                from_date = time_now - timedelta(days=7)
                                
                subquery = SummaryPlayer.objects.filter(
                        player__id=OuterRef('pk')
                    ).filter(created_at__range=[from_date, time_now])
                
                if reward.reward_type == "earned_coins":
                    player_list_order = players_list.annotate(
                        win_coins=Coalesce(
                            Subquery(
                                subquery.values('player')
                                .annotate(total=Sum('earned_coins'))
                                .values('total')[:1],
                                output_field=IntegerField(),
                            ),
                            Value(0, output_field=IntegerField())
                        ),
                        loss_coins=Coalesce(
                            Subquery(
                                subquery.values('player')
                                .annotate(total=Sum('loss_coins'))
                                .values("total")[:1],
                                output_field=IntegerField(),
                            ),
                            Value(0, output_field=IntegerField())
                        )
                    ).annotate(
                        balance_value=F("win_coins") - F("loss_coins")
                    ).order_by("-balance_value")
                else:
                    player_list_order = players_list.annotate(
                        balance_value=Coalesce(
                            Subquery(
                                subquery.values('player')
                                .annotate(total=Sum(reward.reward_type))
                                .values('total')[:1],
                                output_field=IntegerField(),
                            ),
                            Value(0, output_field=IntegerField())
                        )
                    ).order_by(f'-balance_value')                   
            elif reward.date_of_month is not None:
                period = "mes"
                from_date = _month_start(time_now)
                                
                subquery = SummaryPlayer.objects.filter(
                        player__id=OuterRef('pk')
                    ).filter(created_at__range=[from_date, time_now])
                
                player_list_order = players_list.annotate(
                    balance_value=Coalesce(
                        Subquery(
                            subquery.values('player')
                            .annotate(total=Sum(reward.reward_type))
                            .values('total')[:1],
                            output_field=IntegerField(),
                        ),
                        Value(0, output_field=IntegerField())
                    )
                ).order_by(f'-balance_value')
            else:
                logger.error(
                    "PlayerReward id=%s sin date_of_week ni date_of_month; se omite.",
                    reward.id,
                )
                continue

            if reward.date_of_week is not None and reward.date_of_month is not None:
                logger.error(
                    "PlayerReward id=%s tiene date_of_week y date_of_month; "
                    "se procesa como semanal.",
                    reward.id,
                )

            # una sola query con LIMIT, sin COUNT adicional.
            candidates = list(player_list_order[: reward.place])
            if len(candidates) < reward.place:
                logger.error(
                    "Premio id=%s (%s, %s°) no entregado: solo %d candidatos.",
                    reward.id, reward.reward_type, reward.place, len(candidates),
                )
                continue

            summary_win = candidates[reward.place - 1]
            balance = summary_win.balance_value or 0

            if balance <= 0:
                logger.error(
                    "Premio id=%s (%s, %s°) no entregado: jugador %s con balance %s.",
                    reward.id, reward.reward_type, reward.place,
                    summary_win.id, balance,
                )
                continue

            types = REWARD_TYPE_LABELS.get(reward.reward_type)
            if types is None:
                logger.error(
                    "reward_type desconocido '%s' en PlayerReward id=%s; se omite.",
                    reward.reward_type, reward.id,
                )
                continue

            whatsapp_url = None
            if summary_win.phone is not None:
                whatsapp_url = get_whatsapp_reward_text(
                    player=summary_win,
                    player_phone=summary_win.phone,
                    reward_type=types,
                    period=period,
                    place=reward.place
                )

            amount_to_pay = reward.amount
            if reward.reward_type == "earned_coins":
                amount_to_pay = min(reward.amount, balance)
            amount_to_pay = max(0, amount_to_pay)

            body_message = (
                f"Has ganado un premio por ser el {reward.place}° lugar con más "
                f"{types} en {'la última semana' if period == 'semana' else 'el último mes'}. "
                "Tienes 7 días para reclamar tu premio."
            )
            description = (
                f"Premio por {reward.place}° lugar de {types} "
                f"con un total de {balance}."
            )

            try:
                with transaction.atomic():
            
                    create_reward_transactions(
                        to_user=summary_win,
                        reward=reward,
                        amount=amount_to_pay,
                        descriptions=description,
                        whatsapp_url=whatsapp_url
                    )                   
                    whatsapp_url_admin = get_whatsapp_reward_text(
                        player=summary_win,
                        player_phone=admin_phone,
                        reward_type=types,
                        period=period,
                        place= reward.place
                    )

                    Notification.objects.create(
                        player=summary_win,
                        title="¡Felicidades!",
                        message=body_message,
                        whatsapp_url=whatsapp_url_admin
                    )
            except Exception:
                logger.exception(
                    "Error entregando premio id=%s a player=%s; se continúa.",
                    reward.id, summary_win.id,
                )
                continue
            
            # FCM fuera de la transacción: es una llamada externa.
            try:
                FCMNOTIFICATION.send_fcm_message(
                        user=summary_win.user,
                        title="¡Felicidades!",
                        body=body_message
                    )
            except Exception:
                logger.exception(
                    "FCM falló para player=%s (premio id=%s).",
                    summary_win.id, reward.id,
                )
