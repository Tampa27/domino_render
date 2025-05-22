from django.contrib import admin
from .models import Player, Bank, DominoGame, Transaction, Marketing
from dominoapp.utils.admin_helpers import AdminHelpers

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
    search_fields = ["alias", "email", "name"]

class StatusTransactionInline(admin.TabularInline):
    model = Transaction.status_list.through
    inline_actions = []
    fields=['status', 'created_at']
    readonly_fields = ('status', 'created_at')
    can_delete = False
    extra = 0
    max_num = 0

    def status(self, instance):
        return instance.status_transaction.status
    
    def created_at(self, instance):
        return instance.status_transaction.created_at

class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "from_user",
        "to_user",
        "amount",
        "time",
        "type",
        "status",
        "game"
    ]
    inlines = [StatusTransactionInline]
    list_filter = [
        "game",
        "type",
        "time"
    ]
    ordering = ["-time"]
    search_fields = ["from_user__alias", "to_user__alias", "from_user__email", "to_user__email"]
    actions = [AdminHelpers.get_pdf_resume_transaction]

    def status(self, obj):
        return obj.status_list.last().status

class MarketingAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "image",
        "approved",
        "created_at",
        "updated_at"
    ]
    list_filter = [
        "created_at",
        "updated_at",
        "approved"
    ]
    list_editable = ["approved"]
    search_fields = [
        "user__name",
        "user__email"
        ]


# Register your models here.
admin.site.register(Player, PlayerAdmin)
admin.site.register(DominoGame, DominoAdmin)
admin.site.register(Bank)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Marketing, MarketingAdmin)