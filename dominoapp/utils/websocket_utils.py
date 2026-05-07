from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

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

    