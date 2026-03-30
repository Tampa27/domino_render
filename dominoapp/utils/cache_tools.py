from django.core.cache import cache
from django.utils import timezone
from dominoapp.models import Player
import json
import logging
logger = logging.getLogger('django')

def update_player_presence_cache(player_id: int, data: dict):
    """Guarda los timestamps en Redis en lugar de la DB"""
    cache_key = f"p_{player_id}"
    timeout = 600 # 10 minutos
    
    try:
        backend = cache.client.get_client()
        # Convertimos el diccionario a una cadena JSON
        serialized_data = json.dumps(data) 
        
        with backend.pipeline() as pipe:
            pipe.set(cache_key, serialized_data) # <--- Ahora es un string, no un dict
            pipe.expire(cache_key, timeout)
            pipe.execute()
    except AttributeError:
        logger.error("El backend de cache no soporta cliente directo. Usando método de fallback.")
        cache.set(cache_key, data, timeout=timeout)
    except Exception as e:
        logger.error(f"Error guardando en cache: {e}")
    return data

def get_player_presence(player_db_instance: Player):
    """
    Busca la presencia en Redis usando el cliente nativo para optimizar la consulta.
    Si no existe, utiliza los datos de la instancia de la DB.
    """
    cache_key = f"p_{player_db_instance.id}"
    presence = None

    try:
        # Obtenemos el cliente de Redis (asumiendo django-redis)
        backend = cache.client.get_client()
        
        # El pipeline aquí nos permite obtener el valor y, opcionalmente, 
        # resetear el TTL en un solo viaje si quisiéramos.
        with backend.pipeline() as pipe:
            pipe.get(cache_key)
            result = pipe.execute()
            presence = result[0] # El resultado de pipe.get
            
        # Nota: redis nativo devuelve bytes o None, 
        # django-redis suele manejar la serialización automáticamente si se usa el cliente del backend.
    except Exception:
        # Fallback al método estándar de Django si falla el acceso nativo
        presence = cache.get(cache_key)

    # Si no hay nada en caché, devolvemos lo que hay en la DB
    if not presence:
        return {
            'lastTimeInSystem': player_db_instance.lastTimeInSystem,
            'lastTimeInGame': player_db_instance.lastTimeInGame
        }
    
    # Asegurar que las llaves existan (Merge con datos de DB si faltan campos)
    if 'lastTimeInSystem' not in presence:
        presence['lastTimeInSystem'] = player_db_instance.lastTimeInSystem
    if 'lastTimeInGame' not in presence:
        presence['lastTimeInGame'] = player_db_instance.lastTimeInGame
        
    return presence

def get_list_player_presence(players: list[Player])-> dict:
    """
    Obtiene la presencia de una lista de jugadores usando un solo pipeline de Redis.
    """
    if not players:
        return {}

    # 1. Preparar las llaves y el mapeo
    player_ids = [p.id for p in players]
    cache_keys = [f"p_{p_id}" for p_id in player_ids]
    
    # Intentamos obtener todos los datos en un solo viaje (Round Trip)
    presences_from_cache = []
    try:
        backend = cache.client.get_client()
        # Usamos MGET que es más eficiente que un pipeline de GETs individuales
        presences_from_cache = backend.mget(cache_keys)
    except Exception as e:
        logger.error(f"Error accediendo a Redis nativo: {e}")
        # Fallback usando el API estándar de Django (que internamente suele usar mget)
        presences_dict = cache.get_many(cache_keys)
        presences_from_cache = [presences_dict.get(key) for key in cache_keys]

    results = {}
    
    # 2. Procesar resultados y mezclar con datos de DB si es necesario
    for i, player in enumerate(players):
        presence = presences_from_cache[i]
        
        # Si no hay datos en caché, usamos los de la instancia de DB
        if not presence:
            results[player.id] = {
                'lastTimeInSystem': player.lastTimeInSystem,
                'lastTimeInGame': player.lastTimeInGame
            }
            continue

        # Asegurar consistencia de campos (Merge)
        if 'lastTimeInSystem' not in presence:
            presence['lastTimeInSystem'] = player.lastTimeInSystem
        if 'lastTimeInGame' not in presence:
            presence['lastTimeInGame'] = player.lastTimeInGame
            
        results[player.id] = presence

    return results

def lock_game_player(game_id: int, player_id: int):
    """Ejemplo de función para crear un lock específico para un juego y jugador"""
    lock_key = f"g_{game_id}_p_{player_id}"
    backend = cache.client.get_client()
    return backend.lock(lock_key, timeout=10)