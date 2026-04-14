import urllib.parse
from dominoapp.models import Player

def get_whatsapp_reload_text(player: Player, amount: int, transaction_id:str, player_phone:str, paymentmethod:str=None):
    texto_original = f"""
    Hola *{player.name}*,
                
Tu solicitud de recarga para la cuenta **{player.alias}** en Domino Club por un monto de {amount} pesos ha sido recibida con éxito.
    """
    if paymentmethod:
        if paymentmethod == "saldo":
            method = "📱 Saldo Móvil"
        else:
            method = "💳 Transferencia Bancaria"
            
        texto_original += f"""
    Metodo de Pago: {method}
    """
    else:
        texto_original += f"""
Por favor, elige tu método de pago:
    📱 Saldo Móvil
    💳 Transferencia Bancaria
    """
    texto_original += f"""
**ID de tu solicitud**: {transaction_id}
    """
    
    texto_codificado = urllib.parse.quote(texto_original)
    
    return f"https://wa.me/{player_phone}/?text={texto_codificado}"

def get_whatsapp_extraction_text(player: Player, amount: int, transaction_id:str, player_phone:str):
    texto_original = f"""
    Hola *{player.name}*,
    
Tu solicitud de extraer un monto de {amount} pesos de la cuenta **{player.alias}** en Domino Club ha sido recibida con éxito.
    
**ID de tu solicitud**: {transaction_id}
    """
    texto_codificado = urllib.parse.quote(texto_original)
    
    return f"https://wa.me/{player_phone}/?text={texto_codificado}"

def get_whatsapp_reward_text(player: Player, player_phone:str, reward_type:str, period:str):
    texto_original = f"""
    Hola *{player.name}*,
                
Has ganado un premio por ser el jugador con más {reward_type} en {f'la última {period}' if period == 'semana' else f'el último {period}'} en Domino Club.
"""    
    texto_codificado = urllib.parse.quote(texto_original)
    return f"https://wa.me/{player_phone}/?text={texto_codificado}"


def get_whatsapp_tournament_notify(player: Player, player_phone:str, message:str):
    texto_original = f"""
    Hola *{player.name}*,
                
Has terminado en {message}.
"""    
    texto_codificado = urllib.parse.quote(texto_original)
    return f"https://wa.me/{player_phone}/?text={texto_codificado}"