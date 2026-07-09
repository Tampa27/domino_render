import os
from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from django.db.models import Q, F, Value, Exists, OuterRef, Sum, IntegerField, Subquery
from django.db.models.functions import Coalesce
from dominoapp.models import PlayerReward, SummaryPlayer, Notification, Player, BlockPlayer
from dominoapp.utils.transactions import create_reward_transactions
from dominoapp.utils.fcm_message import FCMNOTIFICATION
from dominoapp.utils.whatsapp_help import get_whatsapp_reward_text
import logging
logger = logging.getLogger("django")


class Command(BaseCommand):
    help = "Find players where some field is win in the SummaryPlayer model."

    def handle(self, *args, **options):
        time_now = now()
        rewards = PlayerReward.objects.filter(
            Q(date_of_week = time_now.weekday())|Q(date_of_month = time_now.day)
        )
        players_list = Player.objects.all().exclude(
            Exists(BlockPlayer.objects.filter(
                    player_blocked__id = OuterRef('id')
                )
            )
        )
        for reward in rewards:
            if reward.date_of_week is not None:
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
                                .values('total')[:1]
                            ),
                            Value(0, output_field=IntegerField())
                        ),
                        loss_coins=Coalesce(
                            Subquery(
                                subquery.values('player')
                                .annotate(total=Sum('loss_coins'))
                                .values('total')[:1]
                            ),
                            Value(0, output_field=IntegerField())
                        )
                    ).annotate(
                        balance_coins=F('win_coins') - F('loss_coins')
                    ).order_by(f'-balance_coins')
                else:
                    player_list_order = players_list.annotate(
                        sum_value=Coalesce(
                            Subquery(
                                subquery.values('player')
                                .annotate(total=Sum(reward.reward_type))
                                .values('total')[:1]
                            ),
                            Value(0, output_field=IntegerField())
                        )
                    ).order_by(f'-sum_value')                   
            elif reward.date_of_month is not None:
                month_now = time_now.month
                if month_now == 1:
                    from_date = time_now.replace(year=time_now.year-1, month=12)
                else:
                    from_date = time_now.replace(month=month_now-1)
                subquery = SummaryPlayer.objects.filter(
                        player__id=OuterRef('pk')
                    ).filter(created_at__range=[from_date, time_now])
                
                player_list_order = players_list.annotate(
                    sum_value=Coalesce(
                        Subquery(
                            subquery.values('player')
                            .annotate(total=Sum(reward.reward_type))
                            .values('total')[:1]
                        ),
                        Value(0, output_field=IntegerField())
                    )
                ).order_by(f'-sum_value')
            else:
                raise("No se definio ninguna fecha exacta")
            
            if player_list_order.exists():
                summary_win = player_list_order[reward.place - 1]
                               
                if summary_win:
                    types = "datas ganadas"
                    if reward.reward_type == "match_wins":
                        types = "partidas ganadas"
                    elif reward.reward_type == "pass_player":
                        types = "jugadores pasados"
                    elif reward.reward_type == "earned_coins":
                        types = "monedas ganadas"
                    elif reward.reward_type == "play_99_game":
                        types = "juegos del 9|9 jugados"
                    elif reward.reward_type == "play_66_game":
                        types = "juegos del 6|6 jugados"
                    elif reward.reward_type == "play_in_pairs":
                        types = "juegos en parejas jugados"
                    elif reward.reward_type == "play_in_single":
                        types = "juegos en solitario jugados"
                    elif reward.reward_type == "play_by_points":
                        types = "juegos por puntos jugados"
                    elif reward.reward_type == "play_without_points":
                        types = "juegos sin puntos jugados"
                    
                    if summary_win.phone is not None:
                        whatsapp_url = get_whatsapp_reward_text(
                            player=summary_win,
                            player_phone=summary_win.phone,
                            reward_type=types,
                            period="semana" if reward.date_of_week is not None else "mes"
                        )
                    create_reward_transactions(
                        to_user=summary_win,
                        reward=reward,
                        amount=reward.amount,
                        descriptions=f"Premio por {reward.place} lugar de {types}.",
                        whatsapp_url=whatsapp_url if summary_win.phone is not None else None
                    )                   

                    FCMNOTIFICATION.send_fcm_message(
                        user=summary_win.user,
                        title="¡Felicidades!",
                        body=f"Has ganado un premio por ser el {reward.place}° lugar con más {types} en {'la última semana' if reward.date_of_week is not None else 'el último mes'}. Tienes 10 días para reclamar tu premio."
                    )
                    
                    admin_phone = os.environ.get('ADMIN_PHONE', None)
                    if not admin_phone:
                        admin_phone = "+5352459418"
                        logger.critical("ADMIN_PHONE no está configurado en las variables de entorno.")
                    
                    whatsapp_url = get_whatsapp_reward_text(
                        player=summary_win,
                        player_phone=admin_phone,
                        reward_type=types,
                        period="semana" if reward.date_of_week is not None else "mes"
                    )

                    Notification.objects.create(
                        player=summary_win,
                        title="¡Felicidades!",
                        message=f"Has ganado un premio por ser el {reward.place}° lugar con más {types} en {'la última semana' if reward.date_of_week is not None else 'el último mes'}. Tienes 10 días para reclamar tu premio.",
                        whatsapp_url=whatsapp_url
                    )

        return