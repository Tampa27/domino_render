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
            'player1__user',  # Optimiza el acceso a player.user para FCM
            'player2__user', 
            'player3__user', 
            'player4__user',
            'tournament'      # Es una ForeignKey directa en DominoGame
        ).prefetch_related(
            'match_game'      # Relación inversa con Match_Game
        )
        
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
                        automaticMove(game.id)
                    except Exception as e:
                        logger.critical(f'Ocurrio una excepcion moviendo una ficha en el juego {str(game.id)},\n Data:(player_index: {game.next_player}, playes_in: {len(players_running)} ),\n error: {str(e)}')    
            elif (game.status == 'fg' and game.perPoints == False) or game.status == 'fi' or (game .status == 'fg' and game.in_tournament):
                try:
                    restargame = True
                    if game.status == 'fg':
                        for player in players_running:
                            diff_time = timezone.now() - player.lastTimeInGame
                            start_in_30_min = timezone.now() + timedelta(minutes=30)
                            if not game.in_tournament and (diff_time.seconds >= ApiConstants.EXIT_GAME_TIME or not game_tools.ready_to_play(game,player) or player.play_tournament or (player.registered_in_tournament and player.registered_in_tournament.start_at <= start_in_30_min)) and player.isPlaying:
                                try:
                                    with transaction.atomic():
                                        game_selected = DominoGame.objects.select_for_update(skip_locked=True).get(id=game.id)
                                        game_tools.exitPlayer(game_selected,player,players,len(players))
                                except Exception as e:
                                    logger.critical(f"Error al expulsar al jugador {player.alias} de la mesa {game.id}, error: {str(e)}")
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
                        automaticStart(game)
                except Exception as e:
                    logger.critical(f'Ocurrio una excepcion comenzando el juego en la mesa {str(game.id)}, error: {str(e)}')    
            elif (game.status == 'fg' or game.status == 'wt' or game.status == 'ready') and not game.in_tournament:
                for player in players:
                    diff_time = timezone.now() - player.lastTimeInGame
                    start_in_30_min = timezone.now() + timedelta(minutes=30)
                    if (diff_time.seconds >= ApiConstants.EXIT_GAME_TIME or not game_tools.ready_to_play(game, player) or (player.registered_in_tournament and player.registered_in_tournament.start_at <= start_in_30_min)) and player.isPlaying:
                        try:
                            with transaction.atomic():
                                game_selected = DominoGame.objects.select_for_update(skip_locked=True).get(id=game.id)
                                game_tools.exitPlayer(game_selected,player,players,len(players))
                                new_players = game_tools.playersCount(game_selected)
                                if game_selected.status == 'wt' and len(new_players)<2:
                                    game_selected.starter=-1
                                    game_selected.board = ""
                                    game_selected.save(update_fields=['starter','board'])
                        except Exception as e:
                            logger.critical(f"Error al expulsar al jugador {player.alias} de la mesa {game.id}, error: {str(e)}")
                    elif (diff_time.seconds >= ApiConstants.AUTO_EXIT_GAME) or (player.registered_in_tournament and player.registered_in_tournament.start_at <= start_in_30_min):
                        try:
                            with transaction.atomic():
                                game_selected = DominoGame.objects.select_for_update(skip_locked=True).get(id=game.id)
                                game_tools.exitPlayer(game_selected,player,players,len(players))
                                new_players = game_tools.playersCount(game_selected)
                                if game_selected.status == 'wt' and len(new_players)<2:
                                    game_selected.starter=-1
                                    game_selected.board = ""
                                    game_selected.save(update_fields=['starter','board'])
                        except Exception as e:
                            logger.critical(f"Error al expulsar al jugador {player.alias} de la mesa {game.id}, error: {str(e)}")
                
                    
                ### Enviar notificacion si falta por completar la mesa
                # if game.status == 'wt' and 1<= len(new_players) < 4 and (not game.password or game.password == ""):
                #     players_id = []
                #     if game.player3 is not None:
                #         diff_time = timezone.now() - game.player3.lastTimeInGame
                #         players_id.append(game.player3.id)
                #         players_id.append(game.player2.id)
                #         players_id.append(game.player1.id)
                #     elif game.player2 is not None:
                #         diff_time = timezone.now() - game.player2.lastTimeInGame
                #         players_id.append(game.player2.id)
                #         players_id.append(game.player1.id)
                #     elif game.player1 is not None:
                #         diff_time = timezone.now() - game.player1.lastTimeInGame
                #         players_id.append(game.player1.id)
                    
                #     if diff_time.seconds > ApiConstants.NOTIFICATION_TIME:
                #         if game.inPairs:
                #             players_notify = Player.objects.filter(
                #                 isPlaying = False,
                #                 send_in_pair_notifications = True
                #                 ).exclude(id__in = players_id).order_by("last_notifications", "-lastTimeInSystem")[:10]
                #         else:
                #             last_notifications = timezone.now() - timedelta(hours=ApiConstants.NOTIFICATION_PLAYER_TIME)
                #             players_notify = Player.objects.filter(
                #                 isPlaying = False,
                #                 last_notifications__lte = last_notifications,
                #                 send_game_notifications = True
                #                 ).exclude(id__in = players_id).order_by("-lastTimeInSystem")[:10]
                #         for player in players_notify:
                #             FCMNOTIFICATION.send_fcm_message(
                #                 player.user,
                #                 title= "🎮 Mesa de Domino Activa",
                #                 body= f"Hay jugadores esperando para jugar, únete a esta partida en Domino Club."
                #             )
                #             player.last_notifications = timezone.now()
                #             player.save(update_fields=['last_notifications'])
                    
    except Exception as error:
        logger.critical(f'Ocurrio una excepcion dentro del automatico de las mesas, error: {str(error)}')
    
    try:
        tournaments = Tournament.objects.filter(active=True).prefetch_related(
            'player_list__user',           # Para notificaciones a todos los inscritos
            'round_in_tournament',         # Preload de Rondas (related_name en Round)
            'round_in_tournament__game_list', # Preload de juegos dentro de cada ronda
            'round_in_tournament__winner_pair_list__player1__user', # Para premios
            'round_in_tournament__winner_pair_list__player2__user'
        )
        for tournament in tournaments:
            now = timezone.now()
            player_list = tournament.player_list.all()            
            diff_start = tournament.start_at - timedelta(minutes=5)
            if  diff_start < now and not tournament.notification_5:
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
                    automaticStart(game)
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
                            automaticStart(game)
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

        
def automaticCoupleStarter(game_id:int):
    try:
        with transaction.atomic():
            game = DominoGame.objects.select_for_update(skip_locked=True).get(id=game_id)
            next = game.next_player
            lastMoveTime = lastMove(game)
            time_diff1 = timezone.now() - lastMoveTime
            logger_api.info("Entro a automaticCouple")
            logger_api.info("La diferencia de tiempo es "+ str(time_diff1.seconds))
            if time_diff1.seconds > ApiConstants.AUTO_WAIT_PATNER:
                game_tools.setWinnerStarterNext1(game,next,next,next)
                game.save(update_fields=["starter", "winner", "next_player", "start_time"])
    except Exception as e:
        logger.critical(f"Error en el inicio del compañero automatico en la mesa {game_id}, error: {str(e)}")


def automaticMove(game_id:int):
    try:
        with transaction.atomic():
            # 1. Bloqueamos el juego y sus 4 posibles jugadores relacionados
            # Usamos skip_locked=True para que si alguien ya está moviendo, este proceso lo ignore
            game = DominoGame.objects.select_for_update(skip_locked=True).get(id=game_id)
            # 1.2. Bloqueamos a los jugadores que YA están sentados de forma independiente
            # Esto evita el error de PostgreSQL
            player_ids = [pid for pid in [game.player1_id, game.player2_id, game.player3_id, game.player4_id] if pid]
            if player_ids:
                # Al hacer list() forzamos la ejecución del select_for_update en la DB
                list(Player.objects.select_for_update().filter(id__in=player_ids))
            
            # 2. Obtenemos las instancias de jugadores BLOQUEADAS
            players_in_game = game_tools.playersCount(game)
            players = list(filter(lambda p: p.isPlaying, players_in_game))
            
            # 3. Identificamos al jugador que le toca mover (ahora es una instancia segura)
            next_idx = game.next_player
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

    except DominoGame.DoesNotExist:
        # Si skip_locked=True está activo y la mesa está bloqueada, .get() no encontrará nada
        pass
    except Exception as e:
        logger.critical(f"Error en el movimiento automático de los jugadores en la mesa {game_id}, error: {str(e)}")

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

def automaticStart(game:DominoGame):
    lastMoveTime = lastMove(game)
    time_diff = timezone.now() - lastMoveTime
    
    if time_diff.seconds > ApiConstants.AUTO_START_WAIT:
        try:
            with transaction.atomic():
                # 1. Bloqueamos el juego y a los 4 jugadores potenciales vinculados
                # Usamos select_related para que los objetos 'player' que pasemos a 
                # startGame1 sean los mismos que están bajo el candado de la DB.
                game_selected = DominoGame.objects.select_for_update(skip_locked=True).get(id=game.id)
                # 1.2 Bloqueamos a los jugadores que YA están sentados de forma independiente
                # Esto evita el error de PostgreSQL
                player_ids = [pid for pid in [game_selected.player1_id, game_selected.player2_id, game_selected.player3_id, game_selected.player4_id] if pid]
                if player_ids:
                    # Al hacer list() forzamos la ejecución del select_for_update en la DB
                    list(Player.objects.select_for_update().filter(id__in=player_ids))
                
                
                # 2. Obtenemos la lista de jugadores bloqueados desde el objeto game_selected
                # No uses la lista 'players' que viene por parámetro, ya que son objetos viejos.
                blocked_players = game_tools.playersCount(game_selected)
            
                # 3. Ejecutamos el inicio del juego
                game_tools.startGame1(game_selected, blocked_players)
                
        except DominoGame.DoesNotExist:
            # Si skip_locked=True hace que no se encuentre la fila, simplemente salimos
            pass
        except Exception as error:
            logger.critical(f"Error en el reinicio automático de la mesa {game.id}, error: {str(error)}")