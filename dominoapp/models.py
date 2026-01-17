from django.db import models
from django.db.models import Q
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils import timezone as timezone_dj
import uuid
from shortuuid.django_fields import ShortUUIDField
from dominoapp.utils.constants import GameStatus, GameVariants, TransactionTypes, TransactionStatus, TransactionPaymentMethod, PaymentStatus, TournamentStatus
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
    lastTimeInSystem = models.DateTimeField(default=timezone_dj.now)
    email = models.CharField(max_length=250, unique=True, null=True, blank=True)
    photo_url = models.URLField(max_length=250, null=True, blank=True)
    name = models.CharField(max_length=50,null=True, blank=True)
    isPlaying = models.BooleanField(default=False)
    send_delete_email = models.BooleanField(default=False)
    inactive_player = models.BooleanField(default=False)
    
    referral_code = ShortUUIDField(
        length=6, max_length=7,
        alphabet="ABCDEFGHJKLMNPQRSTUVWXYZ23456789",
        verbose_name='Referral Code', db_index=True,
        unique=True
    )
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_profiles')
    reward_granted = models.BooleanField(default=False,verbose_name="Reward Granted") ## recompesa Otorgada
    ## Valor ELO de un player (valor que dice el nivel segun partidos ganados y perdidos)
    elo = models.DecimalField(decimal_places=2, max_digits=10, default=1500)
    ## Localizacion del player
    lat = models.DecimalField(max_digits=9, decimal_places=7, null=True, blank=True)
    lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    timezone = models.CharField(max_length=50, default="America/Havana")
    last_notifications = models.DateTimeField(default=timezone_dj.now)
    
    @property
    def total_coins(self):
        return self.earned_coins + self.recharged_coins
    
    @property
    def elo_factor(self):
        if (self.dataLoss + self.dataWins) < 100:
            return 40
        elif (self.dataLoss + self.dataWins) >= 100 and self.elo < 2400:
            return 20
        else:
            return 10

    @property
    def is_block(self):
        return BlockPlayer.objects.filter(player_blocked__id = self.id).exists()
    
    @property
    def play_tournament(self):
        tournaments_list = Tournament.objects.filter(Q(status='ready')|Q(status='ru'), player_list=self)
        if tournaments_list.exists():
            for tournament in tournaments_list:
                round = Round.objects.filter(tournament__id = tournament.id).order_by("-round_no").first()
                
                if round.winner_pair_list.filter(Q(player1__id = self.id)| Q(player2__id=self.id)).exists():
                    return True
                elif round.game_list.filter(
                        Q(player1__id=self.id)|
                        Q(player2__id=self.id)|
                        Q(player3__id=self.id)|
                        Q(player4__id=self.id)
                    ).exists():
                        return True
        return False
        
    def __str__(self):
        return self.alias
    
    class Meta:
        ordering = ['alias']
    
    def save(self, *args, **kwargs):
        if self.elo<0:
            self.elo=0
        return super().save(*args, **kwargs)
    

class Pair(models.Model):
    player1 = models.ForeignKey(Player,related_name="pair_1",on_delete=models.CASCADE)
    player2 = models.ForeignKey(Player,related_name="pair_2",on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        """Forzar la validación al guardar"""
        if self.player1 and self.player2 and self.player1.id == self.player2.id:
            raise ValidationError({
                'El mismo jugador no puede estar en ambas posiciones.'
            })
        super().save(*args, **kwargs)

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

class Tournament(models.Model):
    
    # Limit the models that can have a GenericRelation to this table
    MODEL_CHOICES = models.Q(app_label="dominoapp", model="player") | models.Q(
        app_label="dominoapp", model="pair"
    )
        
    player_list = models.ManyToManyField(Player, related_name="player_list")
    
    place_content_type = models.ForeignKey(ContentType,on_delete=models.CASCADE,null=True,blank=True, limit_choices_to=MODEL_CHOICES)
    
    first_place_object_id = models.PositiveIntegerField(null=True, blank=True)
    first_place = GenericForeignKey('place_content_type', 'first_place_object_id')
    
    second_place_object_id = models.PositiveIntegerField(null=True, blank=True)
    second_place = GenericForeignKey('place_content_type', 'second_place_object_id')
    
    third_place_object_id = models.PositiveIntegerField(null=True, blank=True)
    third_place = GenericForeignKey('place_content_type', 'third_place_object_id')
    
    winner_payout = models.IntegerField(default=0)
    second_payout = models.IntegerField(default=0)
    third_payout = models.IntegerField(default=0)
    
    registration_fee = models.IntegerField(default=0)
      
    deadline = models.DateTimeField(default=timezone_dj.now, help_text="%d-%m-%Y %H:%M:%S")   # Fecha tope de inscripción 
    start_at = models.DateTimeField(default=timezone_dj.now, help_text="%d-%m-%Y %H:%M:%S")   # Fecha en que comienza el torneo.
    end_at = models.DateTimeField(blank=True, null=True)    # Fecha en que finalizo el torneo
    
    status = models.CharField(max_length=32,choices=TournamentStatus.status_choices,default="wt")
    active = models.BooleanField(default=True)
        
    created_time = models.DateTimeField(default=timezone_dj.now)
    tournament_no = models.IntegerField(null=True, blank=True)
    
    ## Reglas del Torneo ###
    variant = models.CharField(max_length=10,choices= GameVariants.variant_choices,default="d6")    
    maxScore = models.IntegerField(default=100)
    inPairs = models.BooleanField(default=True)
    startWinner = models.BooleanField(default=False)
    moveTime = models.SmallIntegerField(default=10)
    min_player = models.IntegerField(default=8)
    max_player = models.IntegerField(default=64)
    number_match_win = models.IntegerField(default=2)
    
    notification_1 = models.BooleanField(default=False)
    notification_30 = models.BooleanField(default=False)
    notification_5 = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.tournament_no:
            self.tournament_no = 1
            numbers = Tournament.objects.all().order_by('tournament_no').values_list('tournament_no',flat=True)
            no = 1            
            for number in numbers:
                if no != int(number):
                    self.tournament_no = no
                    break
                elif no == len(numbers):
                    self.tournament_no = no + 1
                    break
                no += 1
        if self.inPairs:
            pair_content_type = ContentType.objects.get_for_model(Pair)
            self.place_content_type = pair_content_type
        else:
            player_content_type = ContentType.objects.get_for_model(Player)
            self.place_content_type = player_content_type
        return super().save(*args, **kwargs)
    
    class Meta:
        ordering = ["-deadline"]    
    
class DominoGame(models.Model):
    Winner_Player_1 = 0
    Winner_Player_2 = 1
    Winner_Player_3 = 2
    Winner_Player_4 = 3
    Tie_Game  = 4
    Winner_Couple_1 = 5
    Winner_Couple_2 = 6    
    
    player1 = models.ForeignKey(Player,related_name="player1",on_delete=models.CASCADE,null=True,blank=True)
    player2 = models.ForeignKey(Player,related_name="player2",on_delete=models.CASCADE,null=True,blank=True)
    player3 = models.ForeignKey(Player,related_name="player3",on_delete=models.CASCADE,null=True,blank=True)
    player4 = models.ForeignKey(Player,related_name="player4",on_delete=models.CASCADE,null=True,blank=True)                  
    next_player = models.SmallIntegerField(default=-1)
    board = models.CharField(max_length=500,blank=True,default="")
    variant = models.CharField(max_length=10,choices= GameVariants.variant_choices,default="d6")
    start_time = models.DateTimeField(default=timezone_dj.now)
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
    lastTime1 = models.DateTimeField(default=timezone_dj.now,null=True,blank=True)
    lastTime2 = models.DateTimeField(default=timezone_dj.now,null=True,blank=True)
    lastTime3 = models.DateTimeField(default=timezone_dj.now,null=True,blank=True)
    lastTime4 = models.DateTimeField(default=timezone_dj.now,null=True,blank=True)
    startAuto = models.IntegerField(default=2,null=True,blank=True)
    sumAllPoints = models.BooleanField(default=False)
    capicua = models.BooleanField(default=False)
    rounds = models.SmallIntegerField(default=0)
    moveTime = models.SmallIntegerField(default=10)
    created_time = models.DateTimeField(default=timezone_dj.now,null=True,blank=True)
    password = models.CharField(max_length=20,blank=True,default="")
    hours_active = models.IntegerField(default=0,null=True,blank=True)
    table_no = models.IntegerField(null=True, blank=True)
    tournament = models.ForeignKey(Tournament, related_name="game_in_tournament", on_delete=models.SET_NULL, null=True, blank=True)    
        
    def save(self, *args, **kwargs):
        if not self.table_no:            
            numbers = DominoGame.objects.all().order_by('table_no').values_list('table_no',flat=True)
            print(numbers)
            no = 1
            for number in numbers:
                if no != int(number):
                    self.table_no = no
                    break
                elif no == len(numbers):
                    self.table_no = no + 1
                    break
                no += 1
        return super().save(*args, **kwargs)

    @property
    def in_tournament(self, ):
        if self.tournament is not None:
            return True
        return False
    
class Match_Game(models.Model):
    game = models.ForeignKey(DominoGame, related_name="match_game", on_delete=models.SET_NULL, null=True, blank=True)
    count_game = models.IntegerField(default=1)
    player_list = models.ManyToManyField(Player, related_name="players_in_game") # Lista de player en la ronda
    pair_list = models.ManyToManyField(Pair, related_name="pairs_in_game") # Lista de parejas en la ronda
    games_win_team_1 = models.IntegerField(default=0)
    games_win_team_2 = models.IntegerField(default=0)
    start_at = models.DateTimeField(default=timezone_dj.now)   # Fecha en que comienza el partido.
    end_at = models.DateTimeField(blank=True, null=True)    # Fecha en que finalizo el partido
    
    @property
    def is_final_match(self):
        number_match_win = self.game.tournament.number_match_win
        if self.games_win_team_1 == number_match_win or self.games_win_team_2==number_match_win:
            return True
        return False
    
    @property
    def winner_pair_1(self):
        number_match_win = self.game.tournament.number_match_win
        if self.games_win_team_1 == number_match_win:
            return True
        return False
    
    @property
    def winner_pair_2(self):
        number_match_win = self.game.tournament.number_match_win
        if self.games_win_team_2 == number_match_win:
            return True
        return False
    
class Round(models.Model):
    tournament = models.ForeignKey(Tournament, related_name="round_in_tournament", on_delete=models.CASCADE)
    player_list = models.ManyToManyField(Player, related_name="players_in_round") # Lista de player en la ronda
    pair_list = models.ManyToManyField(Pair, related_name="pairs_in_round") # Lista de parejas en la ronda
    round_no = models.IntegerField(null=True, blank=True)
    game_list = models.ManyToManyField(DominoGame, related_name="games_in_round") # lista de mesas que se van a usar en la ronda
    start_at = models.DateTimeField(default=timezone_dj.now)   # Fecha en que comienza la ronda.
    end_at = models.DateTimeField(blank=True, null=True)    # Fecha en que finalizo la ronda
    winner_pair_list = models.ManyToManyField(Pair, related_name="winner_pairs_in_round", null=True, blank=True) # Lista de parejas ganadoras en esta ronda
    
    def save(self, *arg, **kwargs):
        if self.round_no is None:
            existing_rounds = Round.objects.filter(tournament__id=self.tournament.id).order_by('round_no').values_list('round_no', flat=True)
            if existing_rounds.exists():
                no = 1            
                for number in existing_rounds:
                    if no != int(number):
                        self.round_no = no
                        break
                    elif no == len(existing_rounds):
                        self.round_no = no + 1
                        break
                    no += 1
            else:
                self.round_no = 1
        return super().save(*arg, **kwargs)

    @property
    def end_round(self):
        total_wins_pair = self.winner_pair_list.all().count()
        total_pair = self.pair_list.all().count()
        if total_pair // 2 == total_wins_pair:
            return True
        return False
    
    @property
    def final_round(self):
        total_wins_pair = self.winner_pair_list.all().count()
        total_pair = self.pair_list.all().count()
        if total_pair // 2 == 1 and total_wins_pair == 1:
            return True
        return False
    
    
class Bank(models.Model):
    extracted_coins = models.PositiveIntegerField(default=0)
    buy_coins = models.PositiveIntegerField(default=0)
    transfer_coins = models.PositiveIntegerField(default=0)
    tournament_coins = models.PositiveIntegerField(default=0)
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
    whatsapp_url = models.URLField(null=True, blank=True, max_length=1500)
    bank_account = models.ForeignKey(BankAccount, related_name="bank_account_transaction", on_delete=models.SET_NULL, null=True, blank=True)
    
    @property
    def get_status(self):
        last_status = self.status_list.all().order_by('-created_at').first()
        return last_status.status if last_status else 'p'


class CurrencyRate(models.Model):
    code = models.CharField(max_length=15)
    rate_exchange = models.DecimalField(default=0.00, decimal_places=6, max_digits=11)
    inverce_rate_exchange = models.DecimalField(default=0.00, decimal_places=6, max_digits=11, null=True, blank=True)
    

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
    description = models.TextField()
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