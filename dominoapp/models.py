from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
# Create your models here.

class Player(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,null=True,blank=True)
    alias = models.CharField(max_length=32) 
    tiles = models.CharField(max_length=50)
    def __str__(self):
        return self.alias
    
    class Meta:
        ordering = ['alias']
    
class DominoGame(models.Model):
    player1 = models.ForeignKey(Player,related_name="player1",on_delete=models.CASCADE,null=True,blank=True)
    player2 = models.ForeignKey(Player,related_name="player2",on_delete=models.CASCADE,null=True,blank=True)
    player3 = models.ForeignKey(Player,related_name="player3",on_delete=models.CASCADE,null=True,blank=True)
    player4 = models.ForeignKey(Player,related_name="player4",on_delete=models.CASCADE,null=True,blank=True)                   
    next_player = models.SmallIntegerField(default=-1,null=True,blank=True)
    board = models.CharField(max_length=200,blank=True,default="")
    variant = models.CharField(max_length=10,choices=[("d6","Double 6"),("d9","Double 9")],default="d6")
    start_time = models.DateTimeField(default=timezone.now())
    winner = models.SmallIntegerField(default=-1,null=True,blank=True)
    scoreTeam1 = models.IntegerField(default=0,null=True,blank=True)
    scoreTeam2 = models.IntegerField(default=0,null=True,blank=True)
    status = models.CharField(max_length=32,choices=[("wt","waiting_players"),("ru","running"),('ready','ready_to_play'),('fi','finished')],default="wt")
    maxScore = models.IntegerField(default=100,null=True,blank=True)
    inPairs = models.BooleanField(default=False)
    perPoints = models.BooleanField(default=False)
    startWinner = models.BooleanField(default=True)
    lostStartInTie = models.BooleanField(default=True)
    starter = models.SmallIntegerField(default=-1,null=True,blank=True)


    def __str__(self) -> str:
        return '%s %s %s %s' % (
            self.variant,
            self.status,
            self.board,
            self.start_time
        )
    