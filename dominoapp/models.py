from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from shortuuid.django_fields import ShortUUIDField
from dominoapp.utils.constants import GameStatus, GameVariants, TransactionTypes, TransactionStatus, TransactionPaymentMethod, PaymentStatus
# Create your models here.

class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_player')
    alias = models.CharField(max_length=50, db_index=True) 
    tiles = models.CharField(max_length=50,default="")
    phone = models.CharField(max_length=20,blank=True, null=True, validators=[RegexValidator(regex=r'^\+{1}?\d{9,15}$')])
    earned_coins = models.IntegerField(default=0)
    recharged_coins = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    dataWins = models.IntegerField(default=0)
    dataLoss = models.IntegerField(default=0)
    matchWins = models.IntegerField(default=0)
    matchLoss = models.IntegerField(default=0)
    lastTimeInSystem = models.DateTimeField(default=timezone.now)
    email = models.CharField(max_length=250, unique=True, null=True, blank=True)
    photo_url = models.URLField(max_length=250, unique=True, null=True, blank=True)
    name = models.CharField(max_length=50,null=True, blank=True)
    isPlaying = models.BooleanField(default=False)
    inactive_player = models.BooleanField(default=False)
    
    referral_code = ShortUUIDField(
        length=6, max_length=7,
        alphabet="ABCDEFGHJKLMNPQRSTUVWXYZ23456789",
        verbose_name='Referral Code', db_index=True,
        unique=True
    )
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_profiles')
    reward_granted = models.BooleanField(default=False,verbose_name="Reward Granted") ## recompesa Otorgada
    
    @property
    def total_coins(self):
        return self.earned_coins + self.recharged_coins
    
    def __str__(self):
        return self.alias
    
    class Meta:
        ordering = ['alias']

class BankAccount(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='bank_accounts')
    account_number = models.CharField(max_length=50)
    phone = models.CharField(max_length=20,blank=True, null=True, validators=[RegexValidator(regex=r'^\+{1}?\d{9,15}$')])
    created_at = models.DateTimeField(auto_now_add=True)

     # Ensure a player cannot have duplicate bank accounts with the same account number
    class Meta:
        unique_together = ('player', 'account_number')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.account_number
    
class DominoGame(models.Model):
    player1 = models.ForeignKey(Player,related_name="player1",on_delete=models.CASCADE,null=True,blank=True)
    player2 = models.ForeignKey(Player,related_name="player2",on_delete=models.CASCADE,null=True,blank=True)
    player3 = models.ForeignKey(Player,related_name="player3",on_delete=models.CASCADE,null=True,blank=True)
    player4 = models.ForeignKey(Player,related_name="player4",on_delete=models.CASCADE,null=True,blank=True)                  
    next_player = models.SmallIntegerField(default=-1)
    board = models.CharField(max_length=500,blank=True,default="")
    variant = models.CharField(max_length=10,choices= GameVariants.variant_choices,default="d6")
    start_time = models.DateTimeField(default=timezone.now)
    winner = models.SmallIntegerField(default=-1)
    scoreTeam1 = models.IntegerField(default=0)
    scoreTeam2 = models.IntegerField(default=0)
    status = models.CharField(max_length=32,choices=GameStatus.status_choices,default="wt")
    maxScore = models.IntegerField(default=100)
    inPairs = models.BooleanField(default=False)
    perPoints = models.BooleanField(default=False)
    startWinner = models.BooleanField(default=True)
    lostStartInTie = models.BooleanField(default=False)
    starter = models.SmallIntegerField(default=-1)
    leftValue = models.SmallIntegerField(default=-1)
    rightValue = models.SmallIntegerField(default=-1)
    payPassValue = models.IntegerField(default=0)
    payWinValue = models.IntegerField(default=0)
    payMatchValue = models.IntegerField(default=0)
    lastTime1 = models.DateTimeField(default=timezone.now,null=True,blank=True)
    lastTime2 = models.DateTimeField(default=timezone.now,null=True,blank=True)
    lastTime3 = models.DateTimeField(default=timezone.now,null=True,blank=True)
    lastTime4 = models.DateTimeField(default=timezone.now,null=True,blank=True)
    startAuto = models.IntegerField(default=2,null=True,blank=True)
    sumAllPoints = models.BooleanField(default=False)
    capicua = models.BooleanField(default=False)
    rounds = models.SmallIntegerField(default=0)
    moveTime = models.SmallIntegerField(default=10)
    created_time = models.DateTimeField(default=timezone.now,null=True,blank=True)
    password = models.CharField(max_length=20,blank=True,default="")
    hours_active = models.IntegerField(default=0,null=True,blank=True)

class Bank(models.Model):
    extracted_coins = models.PositiveIntegerField(default=0)
    buy_coins = models.PositiveIntegerField(default=0)
    promotion_coins = models.PositiveIntegerField(default=0)
    game_coins = models.PositiveIntegerField(default=0)
    game_played = models.PositiveIntegerField(default=0)
    game_completed = models.PositiveIntegerField(default=0)
    data_played = models.PositiveIntegerField(default=0)
    data_completed = models.PositiveIntegerField(default=0)
    time_created = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-time_created"]

    @property
    def balance(self):
        return self.buy_coins - self.extracted_coins

class Status_Transaction(models.Model):
    status = models.CharField(max_length=32,choices=TransactionStatus.transaction_choices,default="p")
    created_at = models.DateTimeField(auto_now_add=True)


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    from_user = models.ForeignKey(Player,related_name="payer",on_delete=models.PROTECT,null=True,blank=True)
    to_user = models.ForeignKey(Player,related_name="collector",on_delete=models.PROTECT,null=True,blank=True)
    amount = models.DecimalField(default=0, decimal_places=2, max_digits= 9)
    time = models.DateTimeField(auto_now_add=True)
    status_list = models.ManyToManyField(to=Status_Transaction, blank=True, related_name="status_transaction")
    type = models.CharField(max_length=15,choices=TransactionTypes.transaction_type,blank=True, null=True)
    game = models.ForeignKey(DominoGame, related_name="game_transaction",on_delete=models.SET_NULL, null=True, blank=True)
    admin = models.ForeignKey(Player, related_name="admin_user", blank=True, null=True, on_delete=models.PROTECT)
    external_id = models.CharField(max_length=50, null=True, blank=True)
    paymentmethod = models.CharField(max_length=32,choices=TransactionPaymentMethod.payment_choices, null=True, blank=True)
    descriptions = models.CharField(max_length=100, null=True, blank=True)
    bank_account = models.ForeignKey(BankAccount, related_name="bank_account_transaction", on_delete=models.SET_NULL, null=True, blank=True)

    

class Status_Payment(models.Model):
    status = models.CharField(max_length=32,choices=PaymentStatus.payment_choices,default="pending")
    created_at = models.DateTimeField(auto_now_add=True)


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True, db_index=True)
    external_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    status_list = models.ManyToManyField(to=Status_Payment, blank=True, related_name="status_payment")
    transaction = models.ForeignKey(Transaction, related_name="transaction_payment", on_delete=models.SET_NULL, blank=True, null= True)
    user = models.ForeignKey(Player,related_name="payer_payment",on_delete=models.PROTECT)
    amount = models.DecimalField(default=0, decimal_places=2, max_digits= 9)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_time = models.DateTimeField(blank=True, null=True)
    


class Marketing(models.Model):
    user = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="user_creator")
    # image = models.ImageField(upload_to='media') # Por el momento se guarda el url hasta que logre poner a guardar los ficheros
    image = models.URLField()
    text = models.CharField(max_length=250, blank=True, null = True)
    url = models.URLField(blank=True, null= True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now= True)
    approved = models.BooleanField(default=False)


class AppVersion(models.Model):
    version = models.CharField(max_length=100, unique=True, db_index=True)
    store_link = models.CharField(max_length=100,null=True, blank=True)
    description = models.TextField(max_length=100)
    need_update = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class BlockPlayer(models.Model):
    player_blocker = models.ForeignKey(Player, on_delete=models.SET_NULL, related_name="blocking_players", null=True)
    player_blocked = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="blocked_by_players")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=['player_blocker', 'player_blocked'],
                name="player_can_only_block_other_player_once",
            )
        ]


class MoveRegister(models.Model):
    game = models.ForeignKey(DominoGame,related_name="game_played",on_delete=models.SET_NULL, null=True, blank=True)
    game_number = models.BigIntegerField()
    board_in_game = models.CharField(max_length=500,blank=True, null=True)
    board_left = models.SmallIntegerField(null=True, blank=True)
    board_right = models.SmallIntegerField(null=True, blank=True)
    score_team1 = models.IntegerField(default=0)
    score_team2 = models.IntegerField(default=0)
    player_move = models.ForeignKey(Player,related_name="player_move",on_delete=models.SET_NULL, null=True, blank=True)
    player_alias = models.CharField(max_length=50)
    player_tiles = models.CharField(max_length=50)
    player_points = models.IntegerField(default=0)
    tile_move = models.CharField(max_length=10)
    players_in_game = models.ManyToManyField(Player, related_name='active_player')
    time = models.DateTimeField(auto_now_add=True)
    play_automatic = models.BooleanField(default=False)
    transactions_list = models.ManyToManyField(to=Transaction, blank=True, related_name="transaction_for_movement")

class ReferralPlayers(models.Model):
    referrer_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="referral_player")
    created_at = models.DateTimeField(auto_now_add=True)
    referral_code = models.CharField(max_length=100, unique=True, db_index=True)
    
    class Meta:
        ordering = ["-created_at"]