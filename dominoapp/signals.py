from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.core.files.storage import default_storage


@receiver([post_delete], sender="dominoapp.Marketing")
def eliminar_archivos_al_borrar(sender, instance, **kwargs):
    """
    Elimina los archivos asociados cuando se borra una instancia del modelo
    """
    if hasattr(instance, 'image') and instance.image:
        default_storage.delete(instance.image.name)

@receiver([post_save], sender="dominoapp.Marketing")
def eliminar_archivos_antiguos_al_actualizar(sender, instance, **kwargs):
    """
    Elimina los archivos antiguos cuando se actualiza una instancia del modelo
    """
    if not instance.pk:
        return False
        
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return False
        
    # Para el campo imagen
    if hasattr(instance, 'image'):
        old_file = old_instance.image
        new_file = instance.image
        if old_file and old_file != new_file:
            default_storage.delete(old_file.name)
