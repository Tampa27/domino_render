import os
from datetime import datetime
from dominoapp.models import Player, Transaction

def validate_tranfer(from_user: Player, to_user: Player, amount:int):
    """Verificar si se puede hacer la transferencia o no. Requisitos:\n
    1- El maximo a transferir es de 500 monedas.\n
    2- El minimo a transferir es de 20 monedas.\n
    3- to_user no puede tener mas de 100 monedas.\n
    4- El Maximo de transferencias en un dia es 2.
    
    
    Args:
        from_user (Player): PLayer que envia el dinero
        to_user (Player): PLayer que recive el dinero
        amount (int): Cantidad de monedas a transferir

    Returns:
        _type_: Tuple[bool, str]
    """
    MIN_TRANSFER = os.getenv("MIN_TRANSFER")
    MAX_TRANSFER = os.getenv("MAX_TRANSFER")
    TRANSFER_PER_DAY = os.getenv("TRANSFER_PER_DAY")
    TO_USER_COINS_TRANSFER = os.getenv("TO_USER_COINS_TRANSFER")
    
    
    if to_user.total_coins > int(TO_USER_COINS_TRANSFER):
        return False, f"Al usuario que intentas transferir tinene más de {TO_USER_COINS_TRANSFER} monedas."
    
    if amount< int(MIN_TRANSFER):
        return False, f"La transferencia debe ser superior a {MIN_TRANSFER} monedas."
    
    if amount> int(MAX_TRANSFER):
        return False, f"La transferencia no puede exceder las {MAX_TRANSFER} monedas."
    
    to_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    total_transaction = Transaction.objects.filter(from_user__id = from_user.id, type="tr", time__gte = to_day).count()
    
    if total_transaction >= int(TRANSFER_PER_DAY):
        return False, f"Haz excedido el máximo de {TRANSFER_PER_DAY} transferencias por día."
    
    return True, None