from django.apps import AppConfig


class DominoappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dominoapp'

    def ready(self):
        # Importa y registra tus señales aquí
        import dominoapp.signals