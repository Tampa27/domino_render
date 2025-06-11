from dominoapp.models import Player, Status_Transaction, Transaction, DominoGame
import logging
logger = logging.getLogger('django')
logger_api = logging.getLogger(__name__)

def create_game_transactions(amount,game:DominoGame,from_user:Player=None, to_user:Player=None, status=None, descriptions=None):
    
    try:
        if not from_user and not to_user:
            logger.error(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: At least one of the from_user or to_user fields should not be empty")
            return False    
        if not  amount>0:
            logger.error(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: The amount must greater than 0")
            return False
        if not status in ["p", "cp", "cc"]:
            logger.error(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: status is not correct")
            return False
        
        new_status = Status_Transaction.objects.create(status = 'p' if status==None else status)
        new_transaction = Transaction.objects.create(
            from_user = from_user if from_user else None,
            to_user = to_user if to_user else None,
            amount = amount,
            game=game,
            type='gm',
            descriptions = descriptions if descriptions else None
        )
        
        new_transaction.status_list.add(new_status)
    
        logger_api.info(f"Transaction of {amount} pesos satisfactory of {from_user} for {to_user}")
        return True
    except Exception as e:
        print(f"error: {e}")
        logger.critical(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: {e}")
        return False
    

def create_reload_transactions(amount, from_user:Player=None, to_user:Player=None, status=None, admin:Player=None, external_id=None, paymentmethod=None):
    
    try:
        if not from_user and not to_user:
            logger.error(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: At least one of the from_user or to_user fields should not be empty")
            return False    
        if not  amount>0:
            logger.error(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: The amount must greater than 0")
            return False
        if not status in ["p", "cp", "cc"]:
            logger.error(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: status is not correct")
            return False
        
        new_status = Status_Transaction.objects.create(status = 'p' if status==None else status)
        new_transaction = Transaction.objects.create(
            from_user = from_user if from_user else None,
            to_user = to_user if to_user else None,
            amount = amount,
            type="rl", 
            admin = admin if admin else None,
            external_id = external_id if external_id else None,
            paymentmethod = paymentmethod if paymentmethod else None
        )
        
        new_transaction.status_list.add(new_status)
    
        logger_api.info(f"Transaction of {amount} pesos satisfactory of {from_user} for {to_user}")
        return True
    except Exception as e:
        print(f"error: {e}")
        logger.critical(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: {e}")
        return False
    

def create_extracted_transactions(amount, from_user:Player=None, to_user:Player=None, status=None, admin:Player=None, external_id=None, paymentmethod=None):
    
    try:
        if not from_user and not to_user:
            logger.error(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: At least one of the from_user or to_user fields should not be empty")
            return False    
        if not  amount>0:
            logger.error(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: The amount must greater than 0")
            return False
        if not status in ["p", "cp", "cc"]:
            logger.error(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: status is not correct")
            return False
        
        new_status = Status_Transaction.objects.create(status = 'p' if status==None else status)
        new_transaction = Transaction.objects.create(
            from_user = from_user if from_user else None,
            to_user = to_user if to_user else None,
            amount = amount,
            type="ex",
            admin = admin if admin else None,
            external_id = external_id if external_id else None,
            paymentmethod = paymentmethod if paymentmethod else None
        )
        
        new_transaction.status_list.add(new_status)
    
        logger_api.info(f"Transaction of {amount} pesos satisfactory of {from_user} for {to_user}")
        return True
    except Exception as e:
        print(f"error: {e}")
        logger.critical(f"Transaction of {amount} pesos failed of {from_user} for {to_user}, error: {e}")
        return False