from django.contrib import admin
from .models import Player
from .models import DominoGame
from .models import Bank

admin.site.site_title = "DOMINO site admin (DEV)"
admin.site.site_header = "DOMINO administration"
admin.site.index_title = "Site administration"

# Register your models here.
admin.site.register(Player)
admin.site.register(DominoGame)
admin.site.register(Bank)