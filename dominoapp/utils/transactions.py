from dominoapp.models import Player, Status_Transaction, Transaction
import logging

def create_transactions(amount, from_user:Player=None, to_user:Player=None, status=None):
    
    try:
        if not from_user and not to_user:
            logging.error(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: At least one of the from_user or to_user fields should not be empty")
            return False    
        if not  amount>0 and not type(amount)==int:
            logging.error(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: The amount must be integer")
            return False
        if not status in ["p", "cp", "cc"]:
            logging.error(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: status is not correct")
            return False
        
        new_status = Status_Transaction.objects.create(status = 'p' if status==None else status)
        new_transaction = Transaction.objects.create(
            from_user = from_user if from_user else None,
            to_user = to_user if to_user else None,
            amount = amount
        )
        
        new_transaction.status_list.add(new_status)
    
        logging.info(f"Transaction of {amount} pesos satisfactory of {from_user} for {to_user}")
        return True
    except Exception as e:
        print(f"error: {e}")
        logging.error(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: {e}")
        return False