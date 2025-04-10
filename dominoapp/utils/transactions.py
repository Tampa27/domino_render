from dominoapp.models import Player, Status_Transaction, Transaction
import logging

def create_transactions(amount, from_user:Player=None, to_user:Player=None, status=None):

    try:
        if not from_user and not to_user:
            raise("At least one of the from_user or to_user fields should not be empty")
        if not  amount>0 and not type(amount)==int:
            raise("The amount must be integer")
        if not status in Status_Transaction.choices:
            raise("status is not correct")
        
        new_status = Status_Transaction.objects.create(status = 'p' if status==None else status)
        new_transaction = Transaction.objects.create(
            from_user = from_user if from_user else None,
            to_user = to_user if to_user else None,
            amount = amount
        )
        new_transaction.status_list.add(new_status)
        new_transaction.save()
        logging.info(f"Transaction of {amount} pesos satisfactory of {from_user} for {to_user}")
    except Exception as e:
        logging.info(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: {e}")