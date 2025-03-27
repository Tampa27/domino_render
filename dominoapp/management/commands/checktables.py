#from django.core.management.base import BaseCommand

#class Command(BaseCommand):
#    def handle(self, *args, **options):
        
#        player = Player.objects.get(alias="mariocondepr")
#        player.coins-=1
#        player.save()
#        time.sleep(10)
#        return super().handle(*args, **options)

import time
import sys
import os
import django

# Configurar entorno Django
PROJECT_ROOT = '/home/ahmedlp9/domino_render'
sys.path.append(PROJECT_ROOT)  # Ruta absoluta a tu proyecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from dominoapp import views
from dominoapp.models import Player
# Importar tus módulos después de configurar Django
#from tu_app import tasks  # Ejemplo de importación

def main():
    while True:
        try:
            # Ejecutar tus tareas
            #tasks.mi_tarea()  # Ejemplo de llamada a otro archivo
            print("Tarea ejecutada correctamente")
        except Exception as e:
            print(f"Error: {str(e)}")
        
        time.sleep(10)  # Esperar 5 segundos

if __name__ == "__main__":
    main()      
