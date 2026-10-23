import logging
from celery import current_app

logger = logging.getLogger("django")

def safe_async_task(task_func, *args, **kwargs):
    """
    Lanza tarea asíncrona. Si el encolado falla, se ejecuta síncronamente como fallback.
    No depende de broker_connection().connected (siempre devuelve False por lazy connection).
    """
    try:
        # Intentar encolar directamente
        result = task_func.apply_async(args=args, kwargs=kwargs, throw=True)
        return result
    except Exception as e:
        logger.error(f"Error encolando {task_func.__name__}: {e}")
        # Fallback: ejecución síncrona
        try:
            return task_func(*args, **kwargs)
        except Exception as fallback_error:
            logger.critical(f"Error en fallback síncrono: {fallback_error}")
            return None

def enqueue_heavy_task(task_func, *args, **kwargs):
    """
    Encola una tarea PESADA (PDF, email con adjunto, exportaciones).
    - NUNCA ejecuta síncronamente: si el broker falla, solo se loguea.
    - Esto evita bloquear la request HTTP y provocar timeouts (Heroku 30s).
    
    El usuario recibe un mensaje de "en breve" y la tarea se reintenta
    según la política del worker (max_retries, etc.).
    """
    try:
        return task_func.apply_async(args=args, kwargs=kwargs)
    except Exception as e:
        logger.error(
            f"No se pudo encolar la tarea pesada {task_func.__name__}: {e}",
            exc_info=True,
        )
        return None