from django.core.cache import cache
from django.utils import timezone
from dominoapp.models import Player

def update_player_presence_cache(player_id: int, data: dict):
    """Guarda los timestamps en Redis en lugar de la DB"""
    # Guardamos por 10 minutos (suficiente para el flujo del juego)
    cache.set(f"player_presence_{player_id}", data, timeout=600)
    return data

def get_player_presence(player_db_instance: Player):
    """Busca en Redis, si no existe, usa lo que hay en DB"""
    presence = cache.get(f"player_presence_{player_db_instance.id}")
    if not presence:
        return {
            'lastTimeInSystem': player_db_instance.lastTimeInSystem,
            'lastTimeInGame': player_db_instance.lastTimeInGame
        }
    if not 'lastTimeInSystem' in presence:
        presence['lastTimeInSystem'] = player_db_instance.lastTimeInSystem
    if not 'lastTimeInGame' in presence:
        presence['lastTimeInGame'] = player_db_instance.lastTimeInGame 
    return presence