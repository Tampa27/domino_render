from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django_admin_listfilter_dropdown.filters import SimpleListFilter
from datetime import datetime, timedelta
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from .models import Player, Bank, DominoGame, Transaction, Marketing, BlockPlayer, MoveRegister, AppVersion, Payment, ReferralPlayers
from dominoapp.utils.admin_helpers import AdminHelpers

admin.site.site_title = "DOMINO site admin (DEV)"
admin.site.site_header = "DOMINO administration"
admin.site.index_title = "Site administration"

class DominoAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "table_no",
        "variant",
        "status",
        "player1",
        "player2",
        "player3",
        "player4",
        "start_time"
    ]

class PlayerAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "alias",
        "email",
        "name",
        "earned_coins",
        "recharged_coins",
        "points",
        "isPlaying",
        "lastTimeInSystem"
    ]
    search_fields = ["alias", "email", "name"]

class PlayerBlockAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "player_blocked",
        "player_blocker",
        "created_at"
    ]
    list_filter = []
    
    search_fields = [
        "player_blocked__name",
        "player_blocked__email",
        "player_blocked__alias",
        "player_blocker__name",
        "player_blocker__email",
        "player_blocker__alias"
        ]

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

class AdminFilter(SimpleListFilter):
    title = "admin"
    parameter_name = "admin"

    def lookups(self, request, model_admin):
        return list(Player.objects.filter(user__is_staff=True).values_list("id", "alias"))

    def queryset(self, request, queryset):
        admin = self.value()
        if admin:
            return queryset.filter(admin__id=admin)
        return queryset

class FromTimeFilter(SimpleListFilter):
    title = "from_date"
    parameter_name = "from_date"

    def lookups(self, request, model_admin):
        now = timezone.now()
        today = now.date().strftime("%d/%m/%Y")
        past_seven = (now - timedelta(days=7)).date().strftime("%d/%m/%Y")
        this_month = (now.replace(day=1)).date().strftime("%d/%m/%Y")
        past_month = (now + relativedelta(months=-1)).replace(day=1).date().strftime("%d/%m/%Y")
        this_year = (now.replace(day=1, month=1)).date().strftime("%d/%m/%Y")
        
        lookups_list = [
            (f'{today}', 'Today'),
            (f'{past_seven}', 'Past 7 days'),
            (f'{this_month}', 'This month'),
            (f'{past_month}', 'Past month'),
            (f'{this_year}', 'This year')
        ]
        
        # Agregar los últimos 15 días
        lookups_list[2:2] = [  # Insertar después del segundo elemento
            (f'{(now - timedelta(days=i)).date().strftime("%d/%m/%Y")}', 
            f'{(now - timedelta(days=i)).date().strftime("%d/%m/%Y")}') 
            for i in range(8,16)
        ]
        
        # Agregar los últimos 6 días
        lookups_list[1:1] = [  # Insertar después del primer elemento
            (f'{(now - timedelta(days=i)).date().strftime("%d/%m/%Y")}', 
            f'{(now - timedelta(days=i)).date().strftime("%d/%m/%Y")}') 
            for i in range(1, 7)
        ]
        
        return lookups_list

    def queryset(self, request, queryset):
        value = self.value()        
        if not value:
            return queryset
        date = datetime.strptime(value, "%d/%m/%Y")
        result = queryset.filter(time__date__gte=date)
        return result
 
class ToTimeFilter(SimpleListFilter):
    title = "to_date"
    parameter_name = "to_date"

    def lookups(self, request, model_admin):
        now = timezone.now()
        today = now.date().strftime("%d/%m/%Y")
        past_seven = (now - timedelta(days=7)).date().strftime("%d/%m/%Y")
        this_month = (now.replace(day=1)).date().strftime("%d/%m/%Y")
        
        lookups_list = [
            (f'{today}', 'Today'),
            (f'{past_seven}', 'Past 7 days'),
            (f'{this_month}', 'This month')
        ]
        
        # Agregar los últimos 15 días
        lookups_list[2:2] = [  # Insertar después del segundo elemento
            (f'{(now - timedelta(days=i)).date().strftime("%d/%m/%Y")}', 
            f'{(now - timedelta(days=i)).date().strftime("%d/%m/%Y")}') 
            for i in range(8,16)
        ]
        
        # Agregar los últimos 6 días
        lookups_list[1:1] = [  # Insertar después del primer elemento
            (f'{(now - timedelta(days=i)).date().strftime("%d/%m/%Y")}', 
            f'{(now - timedelta(days=i)).date().strftime("%d/%m/%Y")}') 
            for i in range(1, 7)
        ]
        
        return lookups_list

    def queryset(self, request, queryset):
        value = self.value()        
        if not value:
            return queryset
        date = datetime.strptime(value, "%d/%m/%Y")
        return queryset.filter(time__date__lt=date)

class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "status",
        "from_user",
        "to_user",
        "amount",
        "time",
        "type",
        "game",
        "descriptions"
    ]
    inlines = [StatusTransactionInline]
    list_filter = [
        "game",
        "type",
        AdminFilter,
        FromTimeFilter,
        ToTimeFilter
    ]
    ordering = ["-time"]
    search_fields = ["from_user__alias", "to_user__alias", "from_user__email", "to_user__email"]
    actions = [AdminHelpers.get_pdf_resume_transaction]

    def status(self, obj):
        return obj.status_list.last().status

class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "amount",
        "external_id",
        "status",
        "created_at",
        "paid_time",
        "transaction"
    ]
    inlines = []
    list_filter = [
        "user",
        "created_at",
        "paid_time"
    ]
    ordering = ["-paid_time", "-created_at"]
    search_fields = ["user__alias", "user__email", "external_id", "transaction__id"]
    actions = []

    def status(self, obj):
        print(obj)
        return obj.status_list.last().status if obj.status_list.count()>0 else None


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

class TransactionInline(admin.TabularInline):
    model = MoveRegister.transactions_list.through
    inline_actions = []
    fields=['get_id', 'from_user', 'to_user', 'amount', 'type', 'descriptions']
    readonly_fields = fields
    can_delete = False
    extra = 0
    max_num = 0

    def get_id(self, instance):
        url = reverse("admin:dominoapp_transaction_change", args=[instance.transaction.id])
        return format_html(f'<a href="{url}" target="_blank">{instance.transaction.id}</a>')
    get_id.short_description = 'ID'
    
    def from_user(self, instance):
        url = reverse("admin:dominoapp_player_change", args=[instance.transaction.from_user.id])
        return format_html(f'<a href="{url}" target="_blank">{instance.transaction.from_user.alias}</a>')
    
    def to_user(self, instance):
        url = reverse("admin:dominoapp_player_change", args=[instance.transaction.to_user.id])
        return format_html(f'<a href="{url}" target="_blank">{instance.transaction.to_user.alias}</a>')
    
    def amount(self, instance):
        return instance.transaction.amount
    
    def type(self, instance):
        return instance.transaction.type
    
    def descriptions(self, instance):
        return instance.transaction.descriptions

class PlayersInline(admin.TabularInline):
    model = MoveRegister.players_in_game.through
    inline_actions = []
    fields=['alias', 'name', 'email']
    readonly_fields = fields
    can_delete = False
    extra = 0
    max_num = 0

      
    def alias(self, instance):
        url = reverse("admin:dominoapp_player_change", args=[instance.player.id])
        return format_html(f'<a href="{url}" target="_blank">{instance.player.alias}</a>')
    
    def name(self, instance):
        return instance.player.name
    
    def email(self, instance):
        return instance.player.email

class MoveRegisterAdmin(admin.ModelAdmin):
    list_display = [
        "game_number",
        "player_alias",
        "tile_move",
        "board_left",
        "board_right",
        "play_automatic",
        "time"
    ]
    list_filter = [
        "time",
        "player_alias",
        "game_number"
    ]
    list_editable = []
    search_fields = [
        "player_move__name",
        "player_move__alias",
        "player_alias",
        "game_number",
        "game__id"
        ]
    inlines = [TransactionInline, PlayersInline]

class ReferralAdmin(admin.ModelAdmin):
    list_display = [
        "referrer",
        "referral_code",
        "code_date",
        "referred_user",
        "referral_date",
        "reward_granted"
    ]
    list_filter = [
        "referrer",
        "reward_granted"
    ]
    list_editable = []
    search_fields = [
        "referrer__alias",
        "referral_code",
        "referred_user__alias"
        ]

class AppVersionAdmin(admin.ModelAdmin):
    list_display = [
        "version",
        "store_link",
        "description",
        "need_update",
        "created_at"
    ]
    list_filter = [
        "version",
        "need_update",
        "store_link",
        "created_at"
    ]
    list_editable = ["need_update"]
    search_fields = [
        "version"
        ]



class BankAdmin(admin.ModelAdmin):
    list_display = [
        "time_created",
        "buy_coins",
        "extracted_coins",
        "balance",
        "game_coins",
        "data_played",
        "data_completed",
        "game_played",
        "game_completed"
    ]
    list_filter = [
        'time_created'
    ]
    list_editable = []
    search_fields = [
        ]


class ReferralPlayersAdmin(admin.ModelAdmin):
    list_display = [
        "referrer_player",
        "referral_code",
        "created_at"
    ]
    list_filter = [
        "created_at"
    ]
    search_fields = [
        "referrer_player__alias",
        "referral_code"
    ]

# Register your models here.
admin.site.register(Player, PlayerAdmin)
admin.site.register(DominoGame, DominoAdmin)
admin.site.register(Bank, BankAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Marketing, MarketingAdmin)
admin.site.register(BlockPlayer, PlayerBlockAdmin)
admin.site.register(MoveRegister, MoveRegisterAdmin)
admin.site.register(AppVersion, AppVersionAdmin)
admin.site.register(ReferralPlayers, ReferralPlayersAdmin)