from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from dominoapp.utils.constants import WSActions
import logging, redis

logger = logging.getLogger('django')

def send_ws_notification(game_id, payload):
    try:
        channel_layer = get_channel_layer()
                        
        async_to_sync(channel_layer.group_send)(
            f'g_{game_id}',
            {
                "type": "game_update",
                "payload": payload
            }
        )
    except Exception as e:
        logger.error(f"Error en send_ws_notification: {e}")

def send_ws_to_lobby(payload):
    try:
        channel_layer = get_channel_layer()
                        
        async_to_sync(channel_layer.group_send)(
            f'lobby_group',
            {
                "type": "lobby_update",
                "payload": payload
            }
        )
    except Exception as e:
        logger.error(f"Error en send_ws_to_lobby: {e}")

def send_ws_chat_message(chat_id, payload):
    try:
        channel_layer = get_channel_layer()
                        
        async_to_sync(channel_layer.group_send)(
            f'chat_{chat_id}',
            {
                "type": "chat_update",
                "payload": payload
            }
        )
    except Exception as e:
        logger.error(f"Error en send_ws_chat_message: {e}")

def get_count_and_up(game_id:int):
    """
    Obtiene el conteo de actualizaciones y lo incrementa en una mesa de forma síncrona.
    """
    async def _get_count_up():
        try:
            channel_layer = get_channel_layer()
            redis_key = f"count_g_{game_id}"

            # 1. Obtener la conexión a Redis directamente
            # Usamos la conexión de la capa de canales o una directa para el incremento     
            async with channel_layer.connection(0) as conn:
                # Incrementa una sola vez para toda la sala
                current_count = await conn.incr(redis_key)

                # Configurar expiración de 10 minutos (600 segundos)
                # Cada vez que hay un mensaje, el cronómetro de 10 min se reinicia
                await conn.expire(redis_key, 600)

                return current_count
        except Exception as e:
            logger.error(f"Error en get_count_and_up para mesa {game_id}: {e}", exc_info=True)
            return 0
            
    return async_to_sync(_get_count_up)()

def get_count_key(game_id:int):
    """
    Obtiene el conteo de actualizaciones en una mesa de forma síncrona.
    """
    async def _get_count():
        try:
            channel_layer = get_channel_layer()
            redis_key = f"count_g_{game_id}"
            
            # 1. Obtener la conexión a Redis directamente
            # Usamos la conexión de la capa de canales
            async with channel_layer.connection(0) as conn:
                redis_key = f"count_g_{game_id}"
                
                # 1. Obtener el valor actual
                val = await conn.get(redis_key)
                
                # 2. Si no existe, devolvemos 0. Si existe, lo convertimos a entero.
                current_count = int(val) if val is not None else 0

                # 3. Refrescar la expiración de 10 minutos
                if val is not None:
                    await conn.expire(redis_key, 600)
                    
                return current_count
        except Exception as e:
            logger.error(f"Error en get_count_key para mesa {game_id}: {e}", exc_info=True)
            return 0
    
    # Ejecutamos la función asíncrona en un entorno síncrono y devolvemos el resultado
    return async_to_sync(_get_count)()

def delete_count_key(game_id):
    """Elimina el contador de la cache."""

    async def _delete_count():
        try:
            channel_layer = get_channel_layer()
            redis_key = f"count_g_{game_id}"
            
            # 3. Borrar el contador de Redis
            async with channel_layer.connection(0) as conn:
                await conn.delete(redis_key)
                    
                return True
        except Exception as e:
            logger.error(f"Error en delete_key para mesa {game_id}: {e}", exc_info=True)
            return False
    
    # Ejecutamos la función asíncrona en un entorno síncrono y devolvemos el resultado
    return async_to_sync(_delete_count)()

async def async_get_count_lobby_up():
        try:
            channel_layer = get_channel_layer()
            redis_key = f"count_lobby"

            # 1. Obtener la conexión a Redis directamente
            # Usamos la conexión de la capa de canales o una directa para el incremento     
            async with channel_layer.connection(0) as conn:
                # Incrementa una sola vez para toda la sala
                current_count = await conn.incr(redis_key)

                # Configurar expiración de 1 hora (3600 segundos)
                # Cada vez que hay un mensaje, el cronómetro de 1 hora se reinicia
                await conn.expire(redis_key, 3600)

                return current_count
        except Exception as e:
            logger.error(f"Error en get_count_lobby_and_up: {e}", exc_info=True)
            return 0

def get_count_lobby_and_up():
    """
    Obtiene el conteo de actualizaciones en el lobby y lo incrementa de forma síncrona.
    """
            
    return async_to_sync(async_get_count_lobby_up)()

def get_count_lobby_key():
    """
    Obtiene el conteo de actualizaciones en una mesa de forma síncrona.
    """
    async def _get_count():
        try:
            channel_layer = get_channel_layer()
            redis_key = f"count_lobby"
            
            # 1. Obtener la conexión a Redis directamente
            # Usamos la conexión de la capa de canales
            async with channel_layer.connection(0) as conn:                
                # 1. Obtener el valor actual
                val = await conn.get(redis_key)
                
                # 2. Si no existe, devolvemos 0. Si existe, lo convertimos a entero.
                current_count = int(val) if val is not None else 0

                # 3. Refrescar la expiración de 1 hora
                if val is not None:
                    await conn.expire(redis_key, 3600)
                    
                return current_count
        except Exception as e:
            logger.error(f"Error en get_count_lobby_key: {e}", exc_info=True)
            return 0
    
    # Ejecutamos la función asíncrona en un entorno síncrono y devolvemos el resultado
    return async_to_sync(_get_count)()

def get_count_and_up_chat_key(chat_id:str):
    """
    Obtiene el conteo de actualizaciones y lo incrementa en un chat de forma síncrona.
    """
    async def _get_count_up():
        try:
            channel_layer = get_channel_layer()
            redis_key = f"count_chat_{chat_id}"

            # 1. Obtener la conexión a Redis directamente
            # Usamos la conexión de la capa de canales o una directa para el incremento     
            async with channel_layer.connection(0) as conn:
                # Incrementa una sola vez para toda la sala
                current_count = await conn.incr(redis_key)

                # Configurar expiración de 10 minutos (600 segundos)
                # Cada vez que hay un mensaje, el cronómetro de 10 min se reinicia
                await conn.expire(redis_key, 600)

                return current_count
        except Exception as e:
            logger.error(f"Error en get_count_and_up para mesa {chat_id}: {e}", exc_info=True)
            return 0
            
    return async_to_sync(_get_count_up)()

def get_count_chat_key(chat_id:str):
    """
    Obtiene el conteo de actualizaciones en un chat de forma síncrona.
    """
    async def _get_count():
        try:
            channel_layer = get_channel_layer()
            redis_key = f"count_chat_{chat_id}"
            
            # 1. Obtener la conexión a Redis directamente
            # Usamos la conexión de la capa de canales
            async with channel_layer.connection(0) as conn:
                redis_key = f"count_chat_{chat_id}"
                
                # 1. Obtener el valor actual
                val = await conn.get(redis_key)
                
                # 2. Si no existe, devolvemos 0. Si existe, lo convertimos a entero.
                current_count = int(val) if val is not None else 0

                # 3. Refrescar la expiración de 10 minutos
                if val is not None:
                    await conn.expire(redis_key, 600)
                    
                return current_count
        except Exception as e:
            logger.error(f"Error en get_count_chat_key para chat {chat_id}: {e}", exc_info=True)
            return 0
    
    # Ejecutamos la función asíncrona en un entorno síncrono y devolvemos el resultado
    return async_to_sync(_get_count)()

PRESENCE_TTL = 40  # segundos (debe ser > intervalo de ping del cliente)

_redis_client = None

def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
    return _redis_client

def _online_key(game_id: int, player_id: int) -> str:
    return f"game:{int(game_id)}:online:p{int(player_id)}"

def mark_player_online(game_id: int, player_id: int) -> bool:
    """
    Renueva la presencia con TTL.
    Devuelve True si la key NO existía (transición offline→online).
    """
    try:
        r = _get_redis()
        key = _online_key(game_id, player_id)
        existed = r.exists(key)
        r.set(key, "1", ex=PRESENCE_TTL)
        return not bool(existed)
    except Exception as e:
        logger.error(f"mark_player_online error: {e}")
        return False

def refresh_player_online(game_id: int, player_id: int):
    """Solo renueva el TTL (para ping)."""
    try:
        _get_redis().expire(_online_key(game_id, player_id), PRESENCE_TTL)
    except Exception as e:
        logger.error(f"refresh_player_online error: {e}")

def mark_player_offline(game_id: int, player_id: int):
    try:
        _get_redis().delete(_online_key(game_id, player_id))
    except Exception as e:
        logger.error(f"mark_player_offline error: {e}")

def is_player_online(game_id: int, player_id: int) -> bool:
    try:
        return bool(_get_redis().exists(_online_key(game_id, player_id)))
    except Exception as e:
        logger.error(f"is_player_online error: {e}")
        return False

def get_online_players(game_id: int) -> set:
    """Devuelve el set de player_ids online en la mesa (SCAN)."""
    try:
        r = _get_redis()
        pattern = f"game:{int(game_id)}:online:p*"
        result = set()
        for k in r.scan_iter(match=pattern, count=100):
            try:
                pid = int(k.rsplit("p", 1)[1])
                result.add(pid)
            except (ValueError, IndexError):
                continue
        return result
    except Exception as e:
        logger.error(f"get_online_players error: {e}")
        return set()

def notify_player_presence(game_id: int, player_id: int, is_online: bool) -> bool:
    """
    Actualiza la presencia del jugador en Redis (con TTL) y notifica al grupo
    de la mesa SOLO si hubo transición de estado.

    - is_online=True  : offline → online
    - is_online=False : online  → offline

    Devuelve True si se notificó al grupo, False si no hubo cambio.

    Replica la lógica de GameConsumer._set_presence() pero desde código síncrono.
    Seguro en multi-worker porque usa Redis como fuente de verdad.
    """
    try:
        if is_online:
            # mark_player_online devuelve True si la key NO existía (offline→online)
            changed = mark_player_online(game_id, player_id)
        else:
            # offline: solo notificamos si realmente estaba online
            was_online = is_player_online(game_id, player_id)
            mark_player_offline(game_id, player_id)
            changed = was_online
        
        count_key = get_count_and_up(game_id) if changed else get_count_key(game_id)

        if not changed:
            return False

        payload = {
            "a": WSActions.PLAYER_ONLINE,
            "cg": count_key,
            "d": {
                "p": player_id,
                "online": is_online,
            }
        }

        send_ws_notification(game_id=game_id, payload=payload)
        return True

    except Exception as error:
        logger.error(
            f"Error en notify_player_presence mesa {game_id}, player {player_id}, "
            f"online={is_online}: {error}"
        )
        return False