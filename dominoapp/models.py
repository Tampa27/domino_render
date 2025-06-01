from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from dominoapp.utils.constants import GameStatus, GameVariants, TransactionTypes, TransactionStatus
# Create your models here.

class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_player')
    alias = models.CharField(max_length=50) 
    tiles = models.CharField(max_length=50,default="")
    coins = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    dataWins = models.IntegerField(default=0)
    dataLoss = models.IntegerField(default=0)
    matchWins = models.IntegerField(default=0)
    matchLoss = models.IntegerField(default=0)
    lastTimeInSystem = models.DateTimeField(default=timezone.now)
    email = models.CharField(max_length=250, unique=True, null=True, blank=True)
    photo_url = models.URLField(max_length=250, unique=True, null=True, blank=True)
    name = models.CharField(max_length=32,null=True, blank=True)
    isPlaying = models.BooleanField(default=False)
    def __str__(self):
        return self.alias
    
    class Meta:
        ordering = ['alias']
    
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
    balance = models.PositiveIntegerField(default=10000)
    created_coins = models.PositiveIntegerField(default=0)
    extracted_coins = models.PositiveIntegerField(default=0)
    buy_coins = models.PositiveIntegerField(default=0)
    ads_coins = models.PositiveIntegerField(default=0)
    datas_coins = models.PositiveIntegerField(default=0)
    matches_coins = models.PositiveIntegerField(default=0)
    private_tables_coins = models.PositiveIntegerField(default=0)

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

class Marketing(models.Model):
    user = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="user_creator")
    image = models.ImageField(upload_to='media')
    text = models.CharField(max_length=250, blank=True, null = True)
    url = models.URLField(blank=True, null= True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now= True)
    approved = models.BooleanField(default=False)


class AppVersion(models.Model):
    version = models.CharField(max_length=100)
    store_link = models.CharField(max_length=100,null=True, blank=True)
    description = models.TextField(max_length=100)
    need_update = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]