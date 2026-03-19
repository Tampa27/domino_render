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
        # 1. Obtener IDs de juegos candidatos
        games_id = DominoGame.objects.filter(player1__isnull=False).values_list('id', flat=True)
        for game_id in games_id:
            # Lista para recolectar notificaciones y enviarlas fuera del bloqueo
            notifications_queue = []
            try:
                with transaction.atomic():
                    # 2. Definir qué tablas queremos bloquear (self = DominoGame)
                    # Bloqueamos la mesa y las 4 posibles relaciones de jugadores                
                    game = (DominoGame.objects
                            .select_for_update(of=('self',), skip_locked=True)
                            .select_related(
                                'player1__user', 'player2__user', 
                                'player3__user', 'player4__user', 
                                'tournament'
                            )
                            .filter(id=game_id).first())

                    if not game:
                        # Si el juego ya está bloqueado por otro proceso, skip_locked lo saltará
                        continue
                    
                    # Bloquear a los jugadores que SÍ existen
                    # Extraemos los IDs de los jugadores que no son nulos
                    player_ids = [
                        p.id for p in [game.player1, game.player2, game.player3, game.player4] 
                        if p is not None
                    ]
                    
                    if player_ids:
                        # Bloqueamos las filas de la tabla Player. 
                        # list() fuerza a que la consulta se ejecute en este momento.
                        locked_players =  list(Player.objects.select_for_update(skip_locked=True).filter(id__in=player_ids))

                        if len(locked_players) < len(player_ids):
                            # Alguien más está tocando a un jugador, mejor salir y reintentar en 7 seg
                            raise Exception("No se pudieron bloquear a todos los jugadores")

                    # 3. Mapeo seguro de jugadores (ignora Nones para evitar errores)
                    # Esta lista contiene los objetos ya bloqueados por el select_for_update
                    active_players = game_tools.playersCount(game)
                    players_running = [p for p in active_players if p.isPlaying]
                    
                    if game.status == 'ru':
                        is_pair_start = (game.inPairs and game.startWinner and game.winner >= DominoGame.Tie_Game)
                        if is_pair_start:
                            logger_api.info('Esperando al salidor')
                            try:
                                automaticCoupleStarter(game)
                            except Exception as e:
                                logger.critical(f'Ocurrio una excepcion escogiendo el salidor en el juego {str(game.id)}, error: {str(e)}')        
                        else:
                            try:
                                automaticMove(game, players_running)
                            except Exception as e:
                                logger.critical(f'Ocurrio una excepcion moviendo una ficha en el juego {str(game.id)},\n Data:(player_index: {game.next_player}, playes_in: {len(players_running)} ),\n error: {str(e)}')
                    elif (game.status == 'fg' and game.perPoints == False) or game.status == 'fi' or (game .status == 'fg' and game.in_tournament):
                        try:
                            restargame = True
                            if game.status == 'fg':
                                now_time = timezone.now()
                                start_in_30_min = now_time + timedelta(minutes=30)
                                for player in players_running:
                                    diff_time = now_time - player.lastTimeInGame                            
                                    if not game.in_tournament and (diff_time.seconds >= ApiConstants.EXIT_GAME_TIME or not game_tools.ready_to_play(game,player) or player.play_tournament or (player.registered_in_tournament and player.registered_in_tournament.start_at <= start_in_30_min and now_time < player.registered_in_tournament.start_at + timedelta(minutes=5))) and player.isPlaying:
                                        try:
                                            game_tools.exitPlayer(game,player,active_players,len(active_players))
                                        except Exception as e:
                                            logger.critical(f"Error al expulsar al jugador {player.alias} de la mesa {game.id}, error: {str(e)}")
                                active_players = game_tools.playersCount(game)
                                if len(active_players)<2:
                                    restargame = False
                                if game.in_tournament:
                                    match = Match_Game.objects.get(game__id = game.id)
                                    if match.is_final_match:
                                        restargame = False
                                        round = Round.objects.get(tournament__id=game.tournament.id, game_list = game)
                                        if match.winner_pair_1:                                    
                                            round.winner_pair_list.add(match.pair_list.first())
                                            if not round.end_round:
                                                notifications_queue.append({
                                                    'user': match.pair_list.first().player1.user,
                                                    'title': "✅ Partido Completado",
                                                    'body': "Partida ganada. El Torneo continúa tras finalizar los demás partidos. 🎮"
                                                })
                                                
                                                notifications_queue.append({
                                                    'user': match.pair_list.first().player2.user,
                                                    'title': "✅ Partido Completado",
                                                    'body':"Partida ganada. El Torneo continúa tras finalizar los demás partidos. 🎮"
                                                })
                                        
                                        if match.winner_pair_2:
                                            round.winner_pair_list.add(match.pair_list.last())
                                            if not round.final_round:
                                                notifications_queue.append({
                                                    'user': match.pair_list.last().player1.user,
                                                    'title': "✅ Partido Completado",
                                                    'body':"Partida ganada. El Torneo continúa tras finalizar los demás partidos. 🎮"
                                                })
                                                notifications_queue.append({
                                                    'user': match.pair_list.last().player2.user,
                                                    'title': "✅ Partido Completado",
                                                    'body':"Partida ganada. El Torneo continúa tras finalizar los demás partidos. 🎮"
                                                })
                                            
                                        for player in active_players:
                                            game_tools.exitPlayer(game,player,active_players,len(active_players))
                                            active_players = game_tools.playersCount(game)
                                        
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
                                                    notifications_queue.append({
                                                        'user': player.user,
                                                        'title': "🏆 Torneo Finalizado",
                                                        'body':"El torneo ha finalizado. ¡Felicidades a los ganadores de este torneo!"
                                                    })
                                                                                        
                                                ##### asignar premios a los ganadores ############
                                                second_pair = round.pair_list.exclude(id=winner_pair.id).first()
                                                TournamentService.process_pay_winners(game.tournament,winner_pair, second_pair)
                                                ##################################################
                                            else:
                                                for pair in round.winner_pair_list.all():
                                                    notifications_queue.append({
                                                        'user': pair.player1.user,
                                                        'title': "⏰ Recordatorio de inicio",
                                                        'body':"La proxima ronda comienza en 5 minutos. ¡Nos vemos pronto en la mesa!"
                                                    })
                                                    notifications_queue.append({
                                                        'user': pair.player2.user,
                                                        'title': "⏰ Recordatorio de inicio",
                                                        'body':f"La proxima ronda comienza en 5 minutos. ¡Nos vemos pronto en la mesa!"
                                                    })
                                                
                            if restargame:
                                automaticStart(game, active_players)
                        except Exception as e:
                            logger.critical(f'Ocurrio una excepcion comenzando el juego en la mesa {str(game.id)}, error: {str(e)}')    
                    
                # --- FUERA DEL ATOMIC ---
                # Solo se ejecuta si la transacción hizo commit sin errores
                for msg in notifications_queue:
                    try:
                        FCMNOTIFICATION.send_fcm_message(
                            user=msg['user'],
                            title=msg['title'],
                            body=msg['body']
                        )
                    except Exception as e:
                        logger.error(f"Error enviando FCM diferido: {str(e)}")

            except Exception as error:
                logger.critical(f'Ocurrio una excepcion dentro del automatico de la mesa {game_id}, error: {str(error)}')
    except Exception as error:
            logger.critical(f'Ocurrio una excepcion dentro del automatico de las mesas, error: {str(error)}')
                 
    finally:
        import gc
        gc.collect()  # Fuerza liberación de memoria.

def automatic_exit_player():
    """Expulsar de las mesas los players que esten inactivos."""
    try:
        logger_api.info(f"Automatic Exit Inactive Player")
        # 1. Obtener IDs de juegos candidatos
        games = DominoGame.objects.select_related(
                            'player1__user', 'player2__user', 
                            'player3__user', 'player4__user', 
                            'tournament'
                        ).filter(player1__isnull=False, status__in = ['fg', 'wt', 'ready']).exclude(tournament__isnull = True)
        now_time = timezone.now()
        start_in_30_min = now_time + timedelta(minutes=30)
        for game in games:
            try:
                active_players = game_tools.playersCount(game)
                for player in active_players:
                    diff_time = now_time - player.lastTimeInGame
                    if (diff_time.seconds >= ApiConstants.EXIT_GAME_TIME or not game_tools.ready_to_play(game, player) or (player.registered_in_tournament and player.registered_in_tournament.start_at <= start_in_30_min)) and player.isPlaying:
                        try:
                            game_tools.exitPlayer(game,player,active_players,len(active_players))
                        except Exception as e:
                            logger.critical(f"Error al expulsar al jugador {player.alias} de la mesa {game.id}, error: {str(e)}")
                    elif (diff_time.seconds >= ApiConstants.AUTO_EXIT_GAME) or (player.registered_in_tournament and player.registered_in_tournament.start_at <= start_in_30_min):
                        try:
                            game_tools.exitPlayer(game,player,active_players,len(active_players))
                        except Exception as e:
                            logger.critical(f"Error al expulsar al jugador {player.alias} de la mesa {game.id}, error: {str(e)}")
                
                active_players = game_tools.playersCount(game)
                if game.status == 'wt' and len(active_players)<2:
                    game.starter=-1
                    game.board = ""
                    game.save(update_fields=['starter','board'])
                    
            except Exception as error:
                logger.critical(f'Ocurrio una excepcion dentro del automatico de la mesa {game.id} para expulsar un player, error: {str(error)}')
        
    except Exception as error:
        logger.critical(f'Ocurrio una excepcion dentro del automatico de expulsar los players inactivos, error: {str(error)}')         
            
    finally:
        import gc
        gc.collect()  # Fuerza liberación de memoria.

def automatic_tournament():
    try:
        tournaments = Tournament.objects.filter(active=True).prefetch_related(
            'player_list__user',           # Para notificaciones a todos los inscritos
            'round_in_tournament',         # Preload de Rondas (related_name en Round)
            'round_in_tournament__game_list', # Preload de juegos dentro de cada ronda
            'round_in_tournament__winner_pair_list__player1__user', # Para premios
            'round_in_tournament__winner_pair_list__player2__user'
        )
        now = timezone.now()
        for tournament in tournaments:
            player_list = tournament.player_list.all()
            player_in_tournament = player_list.count()
            diff_start = tournament.start_at - timedelta(minutes=5)
            if  diff_start < now and not tournament.notification_5 and int(player_in_tournament) == int(tournament.max_player):
                for player in player_list:
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
                    automaticStart(game, players)
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
                            automaticStart(game, players)
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
        import gc
        gc.collect()  # Fuerza liberación de memoria.

##################################################

def automaticCoupleStarter(game:DominoGame):
    try:
        next = game.next_player
        lastMoveTime = lastMove(game)
        time_diff1 = timezone.now() - lastMoveTime
        logger_api.info("Entro a automaticCouple")
        logger_api.info("La diferencia de tiempo es "+ str(time_diff1.seconds))
        if time_diff1.seconds > ApiConstants.AUTO_WAIT_PATNER:
            game_tools.setWinnerStarterNext1(game,next,next,next)
            game.save(update_fields=["starter", "winner", "next_player", "start_time"])
    except Exception as e:
        logger.critical(f"Error en el inicio del compañero automatico en la mesa {game.id}, error: {str(e)}")

def automaticMove(game: DominoGame, players:list[Player]):
    try:        
        # Identificamos al jugador que le toca mover (ahora es una instancia segura)
        next_idx = game.next_player
        next_idx = game.next_player
        if next_idx >= len(players):
            logger.error(f"Índice {next_idx} fuera de rango para mesa {game.id}")
            return
        player_w = players[next_idx]
        
        MOVE_TILE_TIME = game.moveTime
        time_diff = timezone.now() - lastMove(game)
        player_diff_time = timezone.now() - player_w.lastTimeInSystem
        
        # Lógica de selección de ficha...
        if len(game.board) == 0:
            tile = game_tools.takeRandomTile(player_w.tiles)
            if time_diff.seconds > (MOVE_TILE_TIME + ApiConstants.AUTO_MOVE_WAIT):
                try:    
                    # Al pasar 'player_w' (que viene de select_related), movement()
                    # actualizará la fila bloqueada correctamente.
                    error = game_tools.movement(game, player_w, players, tile, automatic=True)
                    if error is not None:
                        logger.error(f"Error en el movimiento automático del jugador {player_w.alias} en la mesa {game.id}, message: {error}")
                    
                    game_tools.updateLastPlayerTime(game, player_w.alias)  
                except Exception as e:
                    logger.critical(f"Error crítico en el movimiento automático del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")            
        else:
            tile = game_tools.takeRandomCorrectTile(player_w.tiles, game.leftValue, game.rightValue)
            if game_tools.isPass(tile):
                if time_diff.seconds > ApiConstants.AUTO_PASS_WAIT:
                    try:
                        error = game_tools.movement(game, player_w, players, tile, automatic=True)
                        if error is not None:
                            logger.error(f"Error en el movimiento automático del jugador {player_w.alias} en la mesa {game.id}, error: {str(error)}")
                        game_tools.updateLastPlayerTime(game, player_w.alias)  
                    except Exception as e:
                        logger.critical(f"Error en el movimiento automático del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")
            elif time_diff.seconds > (MOVE_TILE_TIME + ApiConstants.AUTO_MOVE_WAIT) or (player_diff_time.seconds > ApiConstants.WAIT_FOR_PLAYER and time_diff.seconds > ApiConstants.AUTO_MOVE_WAIT):
                try:
                    error = game_tools.movement(game, player_w, players, tile, automatic=True)
                    if error is not None:
                        logger.error(f"Error en el movimiento automático del jugador {player_w.alias} en la mesa {game.id}, message: {error}")
                    game_tools.updateLastPlayerTime(game, player_w.alias)  
                except Exception as e:
                    logger.error(f"Error en el movimiento automático del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")
    except Exception as e:
        logger.critical(f"Error en el movimiento automático de los jugadores en la mesa {game.id}, error: {str(e)}")

def lastMove(game: DominoGame):
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

def automaticStart(game:DominoGame, blocked_players:list[Player]):
    lastMoveTime = lastMove(game)
    time_diff = timezone.now() - lastMoveTime
    
    if time_diff.seconds > ApiConstants.AUTO_START_WAIT:
        try:                            
            # Ejecutamos el inicio del juego
            if len(blocked_players) < 2 or (game.inPairs and len(blocked_players) < 4):
                logger.error(f"Error en el reinicio automático de la mesa {game.id}, player_len: {len(blocked_players)}")
            else:
                game_tools.startGame1(game, blocked_players)
        except Exception as error:
            logger.critical(f"Error en el reinicio automático de la mesa {game.id}, error: {str(error)}")