from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from django.db.models import Q, Sum
from dominoapp.models import PlayerReward, SummaryPlayer
from dominoapp.utils.transactions import create_reward_transactions
from dominoapp.utils.fcm_message import FCMNOTIFICATION
from dominoapp.utils.whatsapp_help import get_whatsapp_reward_text

class Command(BaseCommand):
    help = "Find players where some field is win in the SummaryPlayer model."

    def handle(self, *args, **options):
        time_now = now()
        rewards = PlayerReward.objects.filter(
            Q(date_of_week = time_now.weekday())|Q(date_of_month = time_now.day)
        )
        for reward in rewards:
            if reward.date_of_week is not None:
                from_date = time_now - timedelta(days=7)
                annotation = {f'total_{reward.reward_type}': Sum(reward.reward_type)}
                if reward.reward_type == "earned_coins":
                    annotation = {f'total_{reward.reward_type}': Sum(reward.reward_type) - Sum('loss_coins')}
                summary = SummaryPlayer.objects.filter(
                    created_at__gte=from_date,
                    created_at__lte=time_now
                ).annotate(**annotation).filter(**{f'total_{reward.reward_type}__gt': 0}).order_by(f'-total_{reward.reward_type}')
            elif reward.date_of_month is not None:
                month_now = time_now.month
                if month_now == 1:
                    from_date = time_now.replace(year=time_now.year-1, month=12)
                else:
                    from_date = time_now.replace(month=month_now-1)
                annotation = {f'total_{reward.reward_type}': Sum(reward.reward_type)}
                summary = SummaryPlayer.objects.filter(
                    created_at__gte=from_date,
                    created_at__lte=time_now
                ).annotate(**annotation).filter(**{f'total_{reward.reward_type}__gt': 0}).order_by(f'-total_{reward.reward_type}')
            
            if summary.exists():
                firts_summary = summary.first()
                summary_win = summary.filter(**{f'total_{reward.reward_type}': getattr(firts_summary, f'total_{reward.reward_type}')})
                for summary in summary_win:
                    types = "datas ganadas"
                    if reward.reward_type == "matches_win":
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
                    elif reward.reward_type == "play_in_singles":
                        types = "juegos en solitario jugados"
                    elif reward.reward_type == "play_by_points":
                        types = "juegos por puntos jugados"
                    elif reward.reward_type == "play_without_points":
                        types = "juegos sin puntos jugados"
                    
                    if summary.player.phone is not None:
                        whatsapp_url = get_whatsapp_reward_text(
                            player=summary.player,
                            player_phone=summary.player.phone,
                            reward_type=types,
                            period="semana" if reward.date_of_week is not None else "mes"
                        )
                    create_reward_transactions(
                        to_user=summary.player,
                        reward=reward,
                        descriptions=f"Premio por {types} con un total de {getattr(summary, f'total_{reward.reward_type}')}",
                        whatsapp_url=whatsapp_url if summary.player.phone is not None else None
                    )                   

                    FCMNOTIFICATION.send_fcm_message(
                        user=summary.player.user,
                        title="¡Felicidades!",
                        body=f"Has ganado un premio por ser el jugador con más {types} en la última {'semana' if reward.date_of_week is not None else 'mes'}."
                    )

                    ### Agregar notificación para el jugador dentro de la apk (Aun por implementar)

        return