import sys
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.utils.timezone import timedelta, now
from dominoapp.models import Transaction, Status_Transaction
from django.db.models import OuterRef, Subquery
from dominoapp.connectors.discord_connector import DiscordConnector
from dominoapp.utils.transactions import create_promotion_transactions

class Command(BaseCommand):
    help = """
        Delete game transactions with time created greater than 1 week.
        Delete transactions with time created greater than 3 month.
        """

    def handle(self, *args, **options):
        ### Delete game transactions with time created greater than 1 week.
        expired_time = now() - timedelta(weeks= 1)
        
        transaction_models = Transaction.objects.filter(
            type = 'gm',
            time__lt=expired_time
            )

        for transaction in transaction_models.iterator():
            for status in transaction.status_list.all():
                status.delete()
            transaction.delete()
        
        # Change to canceled status the reload and extraction transactions with time created greater than 24 hours.
        expired_time = now() - timedelta(hours= 24)
        
        transaction_models = Transaction.objects.filter(
            type__in = ['rl', 'ex'],
            time__lt=expired_time
            ).annotate(latest_status_name=Subquery(
                Status_Transaction.objects.filter(status_transaction=OuterRef('pk')
        ).order_by('-created_at').values('status')[:1])
        ).filter(latest_status_name='p')
        
        for transaction in transaction_models.iterator():
            new_status = Status_Transaction.objects.create(status = 'cc')
            transaction.status_list.add(new_status)
            # if transaction.type == 'ex':
            #     player = transaction.from_user
            #     player.earned_coins += transaction.amount
            #     player.save(update_fields=['earned_coins'])
            #     create_promotion_transactions(
            #         amount= int(transaction.amount),
            #         to_user= player,
            #         status="cp",
            #         descriptions=f'solicitud de extraccion cancelada por tiempo de espera.'
            #     )
            #     transaction.descriptions = f'se le repuso {transaction.amount} monedas a {player.alias} por no completarse la extraccion.'
            #     transaction.save(update_fields=['descriptions'])
            #     DiscordConnector.send_event(
            #         "Cancelled Extraction",
            #         {
            #             "player": player.alias,
            #             "amount": transaction.amount,
            #             "requested_at": transaction.time
            #         }
            #     )
         
        # Delete transactions with time created greater than 3 month.
        expired_time = now() - timedelta(weeks= 12)
        
        transaction_models = Transaction.objects.filter(
            time__lt=expired_time
            )
        
        for transaction in transaction_models.iterator():
            for status in transaction.status_list.all():
                status.delete()
            transaction.delete()            
        
        return