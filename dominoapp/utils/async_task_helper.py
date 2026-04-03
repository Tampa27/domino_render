import logging
from django.conf import settings
from celery import current_app

logger = logging.getLogger("django")

def safe_async_task(task_func, *args, **kwargs):
    """
    Lanza una tarea asíncrona de forma segura.
    Si falla la conexión, registra el error pero no interrumpe.
    """
    try:
        # Verificar si Celery está disponible
        if current_app.broker_connection().connected:
            return task_func.apply_async(args=args, kwargs=kwargs, throw=False)
        else:
            logger.warning(f"Celery broker no disponible, ejecutando {task_func.__name__} síncronamente")
            # Ejecutar síncronamente como fallback
            return task_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error lanzando tarea asíncrona {task_func.__name__}: {e}")
        # Fallback: ejecutar síncronamente
        try:
            return task_func(*args, **kwargs)
        except Exception as fallback_error:
            logger.critical(f"Error en fallback síncrono: {fallback_error}")
            return None