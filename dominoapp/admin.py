from django.contrib import admin
from .models import Player
from .models import DominoGame
from .models import Bank

admin.site.site_title = "DOMINO site admin (DEV)"
admin.site.site_header = "DOMINO administration"
admin.site.index_title = "Site administration"

class DominoAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "variant",
        "status",
        "inPairs",
        "perPoints",
        "rounds",
        "created_time",
        "hours_active"
    ]

class PlayerAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "alias",
        "email",
        "name",
        "coins",
        "points",
        "isPlaying",
        "lastTimeInSystem"
    ]

# Register your models here.
admin.site.register(Player, PlayerAdmin)
admin.site.register(DominoGame, DominoAdmin)
admin.site.register(Bank)