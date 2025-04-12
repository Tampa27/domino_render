from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
# Create your models here.

class Player(models.Model):
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
    status_choices = [
        ("wt","waiting_players"),
        ("ru","running"),
        ('ready','ready_to_play'),
        ('fi','finished'),
        ('fg','game_finished'),
        ('pa','paused')]
    player1 = models.ForeignKey(Player,related_name="player1",on_delete=models.CASCADE,null=True,blank=True)
    player2 = models.ForeignKey(Player,related_name="player2",on_delete=models.CASCADE,null=True,blank=True)
    player3 = models.ForeignKey(Player,related_name="player3",on_delete=models.CASCADE,null=True,blank=True)
    player4 = models.ForeignKey(Player,related_name="player4",on_delete=models.CASCADE,null=True,blank=True)                  
    next_player = models.SmallIntegerField(default=-1)
    board = models.CharField(max_length=200,blank=True,default="")
    variant = models.CharField(max_length=10,choices=[("d6","Double 6"),("d9","Double 9")],default="d6")
    start_time = models.DateTimeField(default=timezone.now)
    winner = models.SmallIntegerField(default=-1)
    scoreTeam1 = models.IntegerField(default=0)
    scoreTeam2 = models.IntegerField(default=0)
    status = models.CharField(max_length=32,choices=status_choices,default="wt")
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
    choices = [
        ("p", "pending"),
        ("cp", "completed"),
        ("cc", "canceled")
    ]
    status = models.CharField(max_length=32,choices=choices,default="p")
    created_at = models.DateTimeField(auto_now_add=True)

class Transaction(models.Model):
    type_choices = [
        ("rl", "reload"), 
        ("ex", "extraction"),
        ("gm", "game")
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    from_user = models.ForeignKey(Player,related_name="payer",on_delete=models.PROTECT,null=True,blank=True)
    to_user = models.ForeignKey(Player,related_name="collector",on_delete=models.PROTECT,null=True,blank=True)
    amount = models.PositiveIntegerField(default=0)
    time = models.DateTimeField(auto_now_add=True)
    status_list = models.ManyToManyField(to=Status_Transaction, blank=True, related_name="status_transaction")
    type = models.CharField(max_length=15,choices=type_choices,blank=True, null=True)
    game = models.ForeignKey(DominoGame, related_name="game_transaction",on_delete=models.PROTECT, null=True, blank=True)