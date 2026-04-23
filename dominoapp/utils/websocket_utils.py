from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger('django')

def send_ws_notification(game_id, payload):
    try:
        channel_layer = get_channel_layer()
        redis_key = f"count_g_{game_id}"
        
        # 1. Obtener la conexión a Redis directamente
        # Usamos la conexión de la capa de canales o una directa para el incremento
        async def get_count_and_send():
            async with channel_layer.connection(0) as conn:
                # Incrementa una sola vez para toda la sala
                current_count = await conn.incr(redis_key)

                # Configurar expiración de 10 minutos (600 segundos)
                # Cada vez que hay un mensaje, el cronómetro de 10 min se reinicia
                await conn.expire(redis_key, 600)
                
                # Agregamos el contador al payload antes de enviarlo
                payload['cg'] = current_count
                
                await channel_layer.group_send(
                    f'g_{game_id}',
                    {
                        "type": "game_update",
                        "payload": payload
                    }
                )
        
        async_to_sync(get_count_and_send)()

    except Exception as e:
        logger.error(f"Error en send_ws_notification: {e}")

def get_count_key(game_id):
    """
    Obtiene el conteo de actualizaciones en una mesa de forma síncrona.
    """
    async def _get_count():
        try:
            channel_layer = get_channel_layer()
            redis_key = f"count_g_{game_id}"
            
            # 1. Obtener la conexión a Redis directamente
            # Usamos la conexión de la capa de canales o una directa para el incremento
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