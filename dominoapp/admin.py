from django.contrib import admin
from .models import Player
from .models import DominoGame
from .models import Bank

# Register your models here.
admin.site.register(Player)
admin.site.register(DominoGame)
admin.site.register(Bank)