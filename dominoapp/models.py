from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Player(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,null=True,blank=True)
    alias = models.CharField(max_length=32) 

    def __str__(self):
        return self.alias
    
    class Meta:
        ordering = ['alias']
    
