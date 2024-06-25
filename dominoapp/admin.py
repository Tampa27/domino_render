from django.contrib import admin
from .models import Player
from .models import DominoGame

# Register your models here.
admin.site.register(Player)
admin.site.register(DominoGame)