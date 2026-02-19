import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from dominoapp.utils import game_tools
from dominoapp.models import DominoGame, Tournament, User, Match_Game, Round, Player
from dominoapp.utils.fcm_message import FCMNOTIFICATION
from django.utils import timezone
from django.utils.timezone import timedelta
from django.db import connection, transaction
from dominoapp.utils.constants import ApiConstants
from dominoapp.services.tournament_service import TournamentService
import logging
import pytz
logger = logging.getLogger('django')
logger_api = logging.getLogger(__name__)

def automatic_move_in_game():
    try:
        logger_api.info(f"Automatic Move Tile")
        
        games = DominoGame.objects.filter(player1__isnull=False).select_related(
            'player1',  # Precarga player1
            'player2',  # Precarga player2
            'player3',  # Precarga player3
            'player4'   # Precarga player4
        ).iterator()
        
        for game in games:
            players = game_tools.playersCount(game)
            players_running = list(filter(lambda p: p.isPlaying, players))
            if game.status == 'ru':
                possibleStarter = (game.inPairs and game.startWinner and game.winner >= DominoGame.Tie_Game)
                if possibleStarter:
                    logger_api.info('Esperando al salidor')
                    try:
                        automaticCoupleStarter(game.id)
                    except Exception as e:
                        logger.critical(f'Ocurrio una excepcion escogiendo el salidor en el juego {str(game.id)}, error: {str(e)}')        
                else:
                    try:
                        automaticMove(game,players_running)
                    except Exception as e:
                        logger.critical(f'Ocurrio una excepcion moviendo una ficha en el juego {str(game.id)},\n Data:(player_index: {game.next_player}, playes_in: {len(players_running)} ),\n error: {str(e)}')    
            elif (game.status == 'fg' and game.perPoints == False) or game.status == 'fi' or (game .status == 'fg' and game.in_tournament):
                try:
                    restargame = True
                    if game.status == 'fg':
                        for player in players_running:
                            diff_time = timezone.now() - player.lastTimeInSystem
                            start_in_30_min = timezone.now() + timedelta(minutes=30)
                            if not game.in_tournament and (diff_time.seconds >= ApiConstants.EXIT_GAME_TIME or not game_tools.ready_to_play(game,player) or player.play_tournament or (player.registered_in_tournament and player.registered_in_tournament.start_at <= start_in_30_min)) and player.isPlaying:
                                game_tools.exitPlayer(game,player,players,len(players))
                        players = game_tools.playersCount(game)
                        if len(players)<2:
                            restargame = False
                        if game.in_tournament:
                            match = Match_Game.objects.get(game__id = game.id)
                            if match.is_final_match:
                                restargame = False
                                round = Round.objects.get(tournament__id=game.tournament.id, game_list = game)
                                if match.winner_pair_1:                                    
                                    round.winner_pair_list.add(match.pair_list.first())
                                    if not round.end_round:
                                        FCMNOTIFICATION.send_fcm_message(
                                            user= match.pair_list.first().player1.user,
                                            title= "✅ Partido Completado",
                                            body=f"Partida ganada. El Torneo continúa tras finalizar los demás partidos. 🎮"
                                        )
                                        FCMNOTIFICATION.send_fcm_message(
                                            user= match.pair_list.first().player2.user,
                                            title= "✅ Partido Completado",
                                            body=f"Partida ganada. El Torneo continúa tras finalizar los demás partidos. 🎮"
                                        )
                                
                                if match.winner_pair_2:
                                    round.winner_pair_list.add(match.pair_list.last())
                                    if not round.final_round:
                                        FCMNOTIFICATION.send_fcm_message(
                                            user= match.pair_list.last().player1.user,
                                            title= "✅ Partido Completado",
                                            body=f"Partida ganada. El Torneo continúa tras finalizar los demás partidos. 🎮"
                                        )
                                        FCMNOTIFICATION.send_fcm_message(
                                            user= match.pair_list.last().player2.user,
                                            title= "✅ Partido Completado",
                                            body=f"Partida ganada. El Torneo continúa tras finalizar los demás partidos. 🎮"
                                        )
                                    
                                for player in players:
                                    game_tools.exitPlayer(game,player,players,len(players))
                                    players = game_tools.playersCount(game)
                                
                                match.end_at = timezone.now()
                                match.save(update_fields=["end_at"])
                                
                                if round.end_round:
                                    
                                    round.end_at = timezone.now()
                                    round.save(update_fields=["end_at"])
                                    
                                    if round.final_round:
                                        game.tournament.active = False
                                        game.tournament.end_at = timezone.now()
                                        game.tournament.status = 'tf'
                                        game.tournament.save(update_fields=['active','end_at', 'status'])
                                        
                                        winner_pair = round.winner_pair_list.first()
                                        ###### Notificar a los jugadores del torneo
                                        for player in game.tournament.player_list.all():
                                            FCMNOTIFICATION.send_fcm_message(
                                                user= player.user,
                                                title= "🏆 Torneo Finalizado",
                                                body=f"El torneo ha finalizado. ¡Felicidades a los ganadores de este torneo!"
                                            )
                                                                                
                                        ##### asignar premios a los ganadores ############
                                        second_pair = round.pair_list.exclude(id=winner_pair.id).first()
                                        TournamentService.process_pay_winners(game.tournament,winner_pair, second_pair)
                                        ##################################################
                                    else:
                                        for pair in round.winner_pair_list.all():
                                            FCMNOTIFICATION.send_fcm_message(
                                                user= pair.player1.user,
                                                title= "⏰ Recordatorio de inicio",
                                                body=f"La proxima ronda comienza en 5 minutos. ¡Nos vemos pronto en la mesa!"
                                            )
                                            FCMNOTIFICATION.send_fcm_message(
                                                user= pair.player2.user,
                                                title= "⏰ Recordatorio de inicio",
                                                body=f"La proxima ronda comienza en 5 minutos. ¡Nos vemos pronto en la mesa!"
                                            )
                                        
                    if restargame:
                        automaticStart(game,players)
                except Exception as e:
                    logger.critical(f'Ocurrio una excepcion comenzando el juego en la mesa {str(game.id)}, error: {str(e)}')    
            elif (game.status == 'fg' or game.status == 'wt' or game.status == 'ready') and not game.in_tournament:
                for player in players:
                    diff_time = timezone.now() - player.lastTimeInSystem
                    start_in_30_min = timezone.now() + timedelta(minutes=30)
                    if (diff_time.seconds >= ApiConstants.EXIT_GAME_TIME or not game_tools.ready_to_play(game, player) or (player.registered_in_tournament and player.registered_in_tournament.start_at <= start_in_30_min)) and player.isPlaying:
                        game_tools.exitPlayer(game,player,players,len(players))
                    elif (diff_time.seconds >= ApiConstants.AUTO_EXIT_GAME) or (player.registered_in_tournament and player.registered_in_tournament.start_at <= start_in_30_min):
                        game_tools.exitPlayer(game,player,players,len(players))
                
                game.refresh_from_db()
                new_players = game_tools.playersCount(game)
                if game.status == 'wt' and len(new_players)<2:
                    game.starter=-1
                    game.board = ""
                    game.save()
                    
                ### Enviar notificacion si falta por completar la mesa
                if game.status == 'wt' and 1<= len(new_players) < 4:
                    players_id = []
                    if game.player3 is not None:
                        diff_time = timezone.now() - game.player3.lastTimeInSystem
                        players_id.append(game.player3.id)
                        players_id.append(game.player2.id)
                        players_id.append(game.player1.id)
                    elif game.player2 is not None:
                        diff_time = timezone.now() - game.player2.lastTimeInSystem
                        players_id.append(game.player2.id)
                        players_id.append(game.player1.id)
                    elif game.player1 is not None:
                        diff_time = timezone.now() - game.player1.lastTimeInSystem
                        players_id.append(game.player1.id)
                    
                    if diff_time.seconds > ApiConstants.NOTIFICATION_TIME:
                        last_notifications = timezone.now() - timedelta(hours=ApiConstants.NOTIFICATION_PLAYER_TIME)
                        players_notify = Player.objects.filter(
                            isPlaying = False,
                            last_notifications__lte = last_notifications,
                            send_game_notifications = True
                            ).exclude(id__in = players_id).order_by("-lastTimeInSystem")[:10]
                        for player in players_notify:
                            FCMNOTIFICATION.send_fcm_message(
                                player.user,
                                title= "🎮 Mesa de Domino Activa",
                                body= f"Hay jugadores esperando para jugar, únete a esta partida en Domino Club."
                            )
                            player.last_notifications = timezone.now()
                            player.save(update_fields=['last_notifications'])
                    
    except Exception as error:
        logger.critical(f'Ocurrio una excepcion dentro del automatico de las mesas, error: {str(error)}')
    
    try:
        tournaments = Tournament.objects.filter(active=True).iterator()
        for tournament in tournaments:
            # analizar si el numero de player es par
            now = timezone.now()
            if (
                (tournament.deadline < now < tournament.start_at and 
                tournament.player_list.count()%2 != 0 and 
                int(tournament.player_list.count()) < int(tournament.max_player)) or
                (tournament.deadline < now < tournament.start_at and 
                int(tournament.player_list.count()) < int(tournament.min_player))
                ):
                tournament.deadline += timedelta(days=1)
                tournament.start_at += timedelta(days=1)
                tournament.save(update_fields=['deadline', 'start_at'])
                for player in tournament.player_list.all():
                    FCMNOTIFICATION.send_fcm_message(
                        user= player.user,
                        title= "⏰ Fechas del Torneo Corridas",
                        body=f"El torneo se pospuso para el {tournament.start_at.astimezone(pytz.timezone(player.timezone)).strftime('%d-%m-%Y, %H:%M')} debido a inscripciones incompletas. Las inscripciones siguen abiertas hasta el {tournament.deadline.astimezone(pytz.timezone(player.timezone)).strftime('%d-%m-%Y, %H:%M')}."
                    )
                
                ##### Se va a comentar hasta que Ahmed termine las pruebas de notificaciones ##### 
                # FCMNOTIFICATION.send_fcm_global_message(
                #     title="⏰ Últimas horas para inscribirte al torneo",
                #     body= f"⏰ Inscripciones a punto de cerrar. Únete al torneo antes del {tournament.deadline.astimezone(pytz.timezone('America/Havana')).strftime('%d-%m a las %H:%M')}."
                # )
            
            diff_start = tournament.start_at - timedelta(hours=2)
            if  diff_start < now and not tournament.notification_1:
                for player in tournament.player_list.all():
                    FCMNOTIFICATION.send_fcm_message(
                        user= player.user,
                        title= "⏰ Recordatorio de inicio",
                        body=f"Recordatorio: El torneo comienza el {tournament.start_at.astimezone(pytz.timezone(player.timezone)).strftime('%d de %B')} a las {tournament.start_at.astimezone(pytz.timezone(player.timezone)).strftime('%H:%M')}. Te esperamos puntual."
                    )
                tournament.notification_1 = True
                tournament.save(update_fields=['notification_1'])
            
            diff_start = tournament.start_at - timedelta(minutes=30)
            if  diff_start < now and not tournament.notification_30:
                for player in tournament.player_list.all():
                    FCMNOTIFICATION.send_fcm_message(
                        user= player.user,
                        title= "⏰ Recordatorio de inicio",
                        body=f"Recordatorio: El torneo comienza en 30 minutos, a las {tournament.start_at.astimezone(pytz.timezone(player.timezone)).strftime('%H:%M')}. ¡Prepárate para jugar!"
                    )
                tournament.notification_30 = True
                tournament.save(update_fields=['notification_30'])
            
            diff_start = tournament.start_at - timedelta(minutes=5)
            if  diff_start < now and not tournament.notification_5:
                for player in tournament.player_list.all():
                    FCMNOTIFICATION.send_fcm_message(
                        user= player.user,
                        title= "⏰ Recordatorio de inicio",
                        body=f"Recordatorio: El torneo comienza en 5 minutos, a las {tournament.start_at.astimezone(pytz.timezone(player.timezone)).strftime('%H:%M')}. ¡Nos vemos pronto en la mesa!"
                    )
                tournament.notification_5 = True
                tournament.save(update_fields=['notification_5'])
                
                TournamentService.process_order_players_rounds(tournament)

            if tournament.start_at < now and tournament.status == 'ready':
                for game in DominoGame.objects.filter(tournament__id=tournament.id):
                    players = game_tools.playersCount(game)
                    automaticStart(game,players)
                    for player in players:
                        FCMNOTIFICATION.send_fcm_message(
                            user= player.user,
                            title= "🏆 Torneo Iniciado",
                            body= "Entra ya, no te lo pierdas"
                        )
                
                tournament.status = "ru"
                tournament.save(update_fields=["status"])

            if tournament.status == 'ru':
                last_round = Round.objects.filter(tournament__id = tournament.id).order_by("-round_no").first()
                if last_round.status == 'ready' and last_round.start_at + timedelta(seconds=30) < now:
                    for game in last_round.game_list.all():
                        if game.status == 'ready':
                            players = game_tools.playersCount(game)
                            automaticStart(game,players)
                            for player in players:
                                FCMNOTIFICATION.send_fcm_message(
                                    user= player.user,
                                    title= "🚨 Ronda Activa 🚨",
                                    body= "La nueva ronda ya empezó. ¡Únete ahora o te lo pierdes!"
                                )
                
                last_round = Round.objects.filter(tournament__id = tournament.id).order_by("-round_no").first()
                if last_round.end_at is not None and last_round.end_at + timedelta(minutes=5) < now:
                    TournamentService.process_order_players_rounds(tournament, last_round)
            
    except Exception as error:
        logger.critical(f'Ocurrio una excepcion dentro del automatico de los torneos, error: {str(error)}')         
            
    finally:
        connection.close()  # Cierra conexiones a la DB.
        import gc
        gc.collect()  # Fuerza liberación de memoria.

        
def automaticCoupleStarter(game_id):
    with transaction.atomic():
        game = DominoGame.objects.select_for_update().get(id=game_id)
        next = game.next_player
        lastMoveTime = lastMove(game)
        time_diff1 = timezone.now() - lastMoveTime
        logger_api.info("Entro a automaticCouple")
        logger_api.info("La diferencia de tiempo es "+ str(time_diff1.seconds))
        if time_diff1.seconds > ApiConstants.AUTO_WAIT_PATNER:
            game_tools.setWinnerStarterNext1(game,next,next,next)
            game.save(update_fields=["starter", "winner", "next_player", "start_time"])

def automaticMove(game,players):
    next = game.next_player
    player_w = players[next]
    MOVE_TILE_TIME = game.moveTime
    time_diff = timezone.now() - lastMove(game)
    if len(game.board) == 0:
        tile = game_tools.takeRandomTile(player_w.tiles)
        if time_diff.seconds > (MOVE_TILE_TIME+ApiConstants.AUTO_MOVE_WAIT):
            try:
                # with transaction.atomic():
                error = game_tools.movement(game.id,player_w,players,tile,automatic=True)
                if error is not None:
                    logger.error(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, message: {error}")
                game_tools.updateLastPlayerTime(game,player_w.alias)  
                # game_tools.move1(game.id,player_w.alias,tile)
            except Exception as e:
                logger.critical(f"Error critico en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")            
            # game_tools.updateLastPlayerTime(game,player_w.alias)
    else:
        tile = game_tools.takeRandomCorrectTile(player_w.tiles,game.leftValue,game.rightValue)
        if game_tools.isPass(tile):
            if time_diff.seconds > ApiConstants.AUTO_PASS_WAIT:
                try:
                    # with transaction.atomic():
                    error = game_tools.movement(game.id,player_w,players,tile,automatic=True)
                    if error is not None:
                        logger.error(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, error: {str(error)}")
                    game_tools.updateLastPlayerTime(game,player_w.alias)  
                    # game_tools.move1(game.id,player_w.alias,tile)
                except Exception as e:
                    logger.critical(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")
                # game_tools.movement(game,player_w,players,tile)
                # game_tools.updateLastPlayerTime(game,player_w.alias) 
        elif time_diff.seconds > (MOVE_TILE_TIME+ApiConstants.AUTO_MOVE_WAIT):
            try:
                # with transaction.atomic():
                error = game_tools.movement(game.id,player_w,players,tile,automatic=True)
                if error is not None:
                    logger.error(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, message: {error}")
                game_tools.updateLastPlayerTime(game,player_w.alias)  
                # game_tools.move1(game.id,player_w.alias,tile)
            except Exception as e:
                logger.error(f"Error en el movimiento automatico del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")
            # game_tools.movement(game,player_w,players,tile)
            # game_tools.updateLastPlayerTime(game,player_w.alias)        
    # game.save()

def lastMove(game):
    res = game.start_time
    if game.lastTime1 is not None and game.lastTime1 > res:
        res = game.lastTime1
    if game.lastTime2 is not None and game.lastTime2 > res:
        res = game.lastTime2
    if game.lastTime3 is not None and game.lastTime3 > res:
        res = game.lastTime3
    if game.lastTime4 is not None and game.lastTime4 > res:
        res = game.lastTime4
    return res                

def automaticStart(game,players):
    lastMoveTime = lastMove(game)
    time_diff = timezone.now() - lastMoveTime
    if time_diff.seconds > ApiConstants.AUTO_START_WAIT:
        game_tools.startGame1(game.id,players)
