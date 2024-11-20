from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
# Create your models here.

class Player(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,null=True,blank=True)
    alias = models.CharField(max_length=32) 
    tiles = models.CharField(max_length=50,default="")
    coins = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    dataWins = models.IntegerField(default=0)
    dataLoss = models.IntegerField(default=0)
    matchWins = models.IntegerField(default=0)
    matchLoss = models.IntegerField(default=0)
    lastTimeInSystem = models.DateTimeField(default=timezone.now())
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
    board = models.CharField(max_length=200,blank=True,default="")
    variant = models.CharField(max_length=10,choices=[("d6","Double 6"),("d9","Double 9")],default="d6")
    start_time = models.DateTimeField(default=timezone.now())
    winner = models.SmallIntegerField(default=-1)
    scoreTeam1 = models.IntegerField(default=0)
    scoreTeam2 = models.IntegerField(default=0)
    status = models.CharField(max_length=32,choices=[("wt","waiting_players"),("ru","running"),('ready','ready_to_play'),('fi','finished'),('fg','game_finished'),('pa','paused')],default="wt")
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
    lastTime1 = models.DateTimeField(default=timezone.now(),null=True,blank=True)
    lastTime2 = models.DateTimeField(default=timezone.now(),null=True,blank=True)
    lastTime3 = models.DateTimeField(default=timezone.now(),null=True,blank=True)
    lastTime4 = models.DateTimeField(default=timezone.now(),null=True,blank=True)
    startAuto = models.IntegerField(default=2,null=True,blank=True)
    sumAllPoints = models.BooleanField(default=False)
    capicua = models.BooleanField(default=False)
    rounds = models.SmallIntegerField(default=0)
    moveTime = models.SmallIntegerField(default=10)

    def __str__(self) -> str:
        return '%s %s %s %s' % (
            self.variant,
            self.status,
            self.board,
            self.start_time
        )
    