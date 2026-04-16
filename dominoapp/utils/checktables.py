import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'domino.settings')
django.setup()

from dominoapp.utils import game_tools
from dominoapp.models import DominoGame, Tournament, Match_Game, Round, Player
from django.utils import timezone
from django.utils.timezone import timedelta
from django.db import connection, transaction
from django.conf import settings
from dominoapp.utils.constants import ApiConstants
from dominoapp.services.tournament_service import TournamentService
from dominoapp.utils.websocket_consumers import send_ws_notification
from dominoapp.utils.constants import WSActions
import logging
import pytz
logger = logging.getLogger('django')
logger_api = logging.getLogger(__name__)


def procesar_logica_de_mesa(game_id: int):
    start_time = timezone.now()
    try:
        # Obtenemos la mesa con select_related para evitar múltiples queries
        game = DominoGame.objects.select_related(
            'player1__user', 'player2__user', 'player3__user', 'player4__user', 'tournament'
        ).get(id=game_id)

        # 1. Lógica de Movimientos (Antiguo automatic_move_in_game)
        if game.status == 'ru':
            is_pair_start = (game.inPairs and game.startWinner and game.winner >= DominoGame.Tie_Game)
            if is_pair_start:
                automaticCoupleStarter(game)
            else:
                automaticMove(game)

        # 2. Lógica de Reinicio/Finalización (Antiguo automatic_restar_game)
        elif game.status in ['fg', 'fi']:
            # Lógica de la función automatic_restar_game 
            # pero usando la instancia 'game' que ya tenemos
            try:
                if (game.status == 'fg' and game.perPoints == False) or game.status == 'fi' or (game .status == 'fg' and game.in_tournament):
                    try:
                        restargame = True
                        with transaction.atomic():    
                            try:
                                game_block = DominoGame.objects.select_related(
                                    'player1', 'player2', 'player3', 'player4', 'tournament'
                                ).select_for_update(of=('self',), skip_locked=True).get(id=game.id)
                            except Exception as error:
                                return

                            player_ids = [pid for pid in [game_block.player1_id, game_block.player2_id, game_block.player3_id, game_block.player4_id] if pid]
                            active_players = []
                            if player_ids:
                                # Al hacer list() forzamos la ejecución del select_for_update en la DB
                                active_players  = list(Player.objects.select_for_update(skip_locked=True).filter(id__in=player_ids))
                                
                                if len(active_players) < len(player_ids):
                                    # Alguien más está tocando a un jugador, mejor salir y reintentar en 7 seg
                                    return

                            if game_block.status == 'fg':
                                now_time = timezone.now()
                                start_in_30_min = now_time + timedelta(minutes=30)
                                needs_update = False
                                for player in active_players:                                
                                    diff_time = now_time - player.lastTimeInGame
                                    if not game_block.in_tournament and (diff_time.seconds >= ApiConstants.EXIT_GAME_TIME or not game_tools.ready_to_play(game_block,player) or player.play_tournament or (player.registered_in_tournament and player.registered_in_tournament.start_at <= start_in_30_min and now_time < player.registered_in_tournament.start_at + timedelta(minutes=5))) and player.isPlaying:
                                        try:
                                            success = game_tools.exitPlayer(game_block,player,active_players,len(active_players))
                                            if success:
                                                needs_update = True
                                                # Actualizamos la lista local para que la siguiente iteración vea el cambio
                                                active_players = game_tools.playersCount(game_block)
                                        except Exception as e:
                                            logger.critical(f"Error al expulsar al jugador {player.alias} de la mesa {game.id}, error: {str(e)}")
                                
                                if needs_update:
                                    try:
                                        transaction.on_commit(lambda: send_ws_notification(
                                            game_id= game_block.id,
                                            payload={
                                                "a": WSActions.PLAYER_LEFT,
                                                "d": {
                                                    "st": game_block.status
                                                } 
                                            }
                                        ))
                                    except Exception as error:
                                        logger.error(f"Error al enviar el WS en el exit del automatico: {error}")

                                if len(active_players)<2:
                                    restargame = False
                                if game_block.in_tournament:
                                    from dominoapp.tasks import async_send_fcm_message
                                    match = Match_Game.objects.get(game__id = game_block.id)
                                    if match.is_final_match:
                                        restargame = False
                                        round = Round.objects.get(tournament__id=game_block.tournament.id, game_list = game_block)
                                        if match.winner_pair_1:                                    
                                            round.winner_pair_list.add(match.pair_list.first())
                                            if not round.end_round:
                                                try:
                                                    async_send_fcm_message.delay(
                                                        users_id=[match.pair_list.first().player1.user.id, match.pair_list.first().player2.user.id],
                                                        title="✅ Partido Completado",
                                                        message="Partida ganada. El Torneo continúa tras finalizar los demás partidos. 🎮"
                                                    )
                                                except Exception as error:
                                                    logger.error(f'Error al enviar notificacion FCM de partido completado" => {str(error)}')
                                        
                                        if match.winner_pair_2:
                                            round.winner_pair_list.add(match.pair_list.last())
                                            if not round.final_round:
                                                try:
                                                    async_send_fcm_message.delay(
                                                        users_id=[match.pair_list.last().player1.user.id, match.pair_list.last().player2.user.id],
                                                        title="✅ Partido Completado",
                                                        message="Partida ganada. El Torneo continúa tras finalizar los demás partidos. 🎮"
                                                    )
                                                except Exception as error:
                                                    logger.error(f'Error al enviar notificacion FCM de partido completado" => {str(error)}')
                                        
                                        needs_update = False
                                        for player in active_players:
                                            success = game_tools.exitPlayer(game_block,player,active_players,len(active_players))
                                            if success:
                                                needs_update = True
                                                # Actualizamos la lista local para que la siguiente iteración vea el cambio
                                                active_players = game_tools.playersCount(game_block)
                                        
                                        if needs_update:
                                            try:
                                                transaction.on_commit(lambda: send_ws_notification(
                                                    game_id= game_block.id,
                                                    payload={
                                                        "a": WSActions.PLAYER_LEFT,
                                                        "d": {
                                                            "st": game_block.status
                                                        } 
                                                    }
                                                ))
                                            except Exception as error:
                                                logger.error(f"Error enviando el ws en el Start automatico. Error: {error}")
                                        
                                        match.end_at = timezone.now()
                                        match.save(update_fields=["end_at"])
                                        
                                        if round.end_round:
                                            
                                            round.end_at = timezone.now()
                                            round.save(update_fields=["end_at"])
                                            
                                            if round.final_round:
                                                game_block.tournament.active = False
                                                game_block.tournament.end_at = timezone.now()
                                                game_block.tournament.status = 'tf'
                                                game_block.tournament.save(update_fields=['active','end_at', 'status'])
                                                
                                                winner_pair = round.winner_pair_list.first()
                                                ###### Notificar a los jugadores del torneo
                                                players_ids = list(game_block.tournament.player_list.values_list('user_id', flat=True))
                                                try:
                                                    async_send_fcm_message.delay(
                                                        users_id=players_ids,
                                                        title="🏆 Torneo Finalizado",
                                                        message="El torneo ha finalizado. ¡Felicidades a los ganadores de este torneo!"
                                                    )
                                                except Exception as error:
                                                    logger.error(f'Error al enviar notificacion FCM de torneo finalizado" => {str(error)}')
                                                                                                                                    
                                                ##### asignar premios a los ganadores ############
                                                second_pair = round.pair_list.exclude(id=winner_pair.id).first()
                                                TournamentService.process_pay_winners(game_block.tournament,winner_pair, second_pair)
                                                ##################################################
                                            else:
                                                players_ids = list(round.winner_pair_list.values_list('player1__user_id', flat=True)) + list(round.winner_pair_list.values_list('player2__user_id', flat=True))
                                                try:
                                                    async_send_fcm_message.delay(
                                                        users_id=players_ids,
                                                        title="⏰ Recordatorio de inicio",
                                                        message="La proxima ronda comienza en 5 minutos. ¡Nos vemos pronto en la mesa!"
                                                    )
                                                except Exception as error:
                                                    logger.error(f'Error al enviar notificacion FCM de recordatorio de inicio" => {str(error)}')
                                                
                            if restargame:
                                success = automaticStart(game_block, active_players)
                                if success:
                                    try:
                                        transaction.on_commit(lambda: send_ws_notification(
                                            game_id= game_block.id,
                                            payload={
                                                "a": WSActions.GAME_STARTED,
                                                "d": {
                                                    "st": game_block.status
                                                } 
                                            }
                                        ))
                                    except Exception as error:
                                        logger.error(f"Error enviando el ws en el Start automatico. Error: {error}")
                    except Exception as e:
                        logger.critical(f'Ocurrio una excepcion comenzando el juego en la mesa {str(game.id)}, error: {str(e)}')    

            except Exception as error:
                logger.critical(f'Ocurrio una excepcion dentro del restar automatico de la mesa {game.id}, error: {str(error)}, time: {(timezone.now() - start_time).total_seconds()} segundos.')

        # 3. Lógica de Limpieza/Expulsión (Antiguo automatic_exit_player / clear_game)
        if game.status in ['fg', 'wt', 'ready'] and not game.in_tournament:
            now_time = timezone.now()
            start_in_30_min = now_time + timedelta(minutes=30)
            try:
                with transaction.atomic():
                    try:
                        game_block = (DominoGame.objects
                            .select_for_update(of=('self',), skip_locked=True)
                            .select_related(
                                'player1__user', 'player2__user', 
                                'player3__user', 'player4__user'
                            ).get(id=game.id))
                    except Exception as error:
                        return
                    
                    # Bloqueamos a los jugadores que YA están sentados de forma independiente
                    # Esto evita el error de PostgreSQL
                    player_ids = [pid for pid in [game_block.player1_id, game_block.player2_id, game_block.player3_id, game_block.player4_id] if pid]
                    active_players = []
                    if player_ids:
                        # Al hacer list() forzamos la ejecución del select_for_update en la DB
                        active_players  = list(Player.objects.select_for_update(skip_locked=True).filter(id__in=player_ids))
                        
                        if len(active_players) < len(player_ids):
                            # Alguien más está tocando a un jugador, mejor salir y reintentar en 7 seg
                            return

                    needs_update = False
                    for player in active_players:                    
                                       
                        diff_time = now_time - player.lastTimeInGame
                        # Condiciones de expulsión
                        lost_connection = diff_time.seconds >= ApiConstants.EXIT_GAME_TIME
                        is_inactive = diff_time.seconds >= ApiConstants.AUTO_EXIT_GAME
                        not_enough_money = not game_tools.ready_to_play(game_block, player)
                        tournament_soon = player.registered_in_tournament and player.registered_in_tournament.start_at <= start_in_30_min

                        if (lost_connection and player.isPlaying) or (is_inactive)  or tournament_soon  or not_enough_money:
                            # 2. EJECUTAR LÓGICA DE SALIDA
                            # Ojo: exitPlayer debe recibir el objeto bloqueado (game_block)
                            try:
                                success = game_tools.exitPlayer(game_block, player, active_players, len(active_players))
                                if success:
                                    needs_update = True
                                    # Actualizamos la lista local para que la siguiente iteración vea el cambio
                                    active_players = game_tools.playersCount(game_block)
                            except Exception as e:
                                logger.critical(f"Error al expulsar al jugador {player.alias} de la mesa {game.id}, error: {str(e)}")

                    # Solo guardamos si realmente hubo un cambio
                    if needs_update:
                        try:
                            transaction.on_commit(lambda: send_ws_notification(
                                game_id= game_block.id,
                                payload={
                                    "a": WSActions.PLAYER_LEFT,
                                    "d": {
                                        "st": game_block.status
                                    } 
                                }
                            ))
                        except Exception as error:
                            logger.error(f"Error al enviar el WS en el exit del automatico: {error}")
                        if game_block.status == 'wt' and len(active_players)<2:
                            game_block.board = ""
                            game_block.save(update_fields=['board'])
                
                #### Fuera de la transaccion atomica
                active_players = game_tools.playersCount(game)
                if game.status == 'wt' and 1<= len(active_players) < 4 and (not game.password or game.password == ""):
                    players_id = []
                    if game.player3 is not None:
                        diff_time = timezone.now() - game.player3.lastTimeInGame
                        players_id.append(game.player3.id)
                        players_id.append(game.player2.id)
                        players_id.append(game.player1.id)
                    elif game.player2 is not None:
                        diff_time = timezone.now() - game.player2.lastTimeInGame
                        players_id.append(game.player2.id)
                        players_id.append(game.player1.id)
                    elif game.player1 is not None:
                        diff_time = timezone.now() - game.player1.lastTimeInGame
                        players_id.append(game.player1.id)

                    if diff_time.seconds > ApiConstants.NOTIFICATION_TIME:
                        players_list = None
                        if game.inPairs:
                            players_list = Player.objects.filter(
                                isPlaying = False,
                                send_in_pair_notifications = True
                                ).exclude(id__in = players_id).order_by("last_notifications", "-lastTimeInSystem")
                        else:
                            last_notifications = timezone.now() - timedelta(hours=ApiConstants.NOTIFICATION_PLAYER_TIME)
                            players_list = Player.objects.filter(
                                isPlaying = False,
                                last_notifications__lte = last_notifications,
                                send_game_notifications = True
                                ).exclude(id__in = players_id).order_by("-lastTimeInSystem")
                        
                        print("players_list: ", players_list)
                        if players_list:
                            from dominoapp.tasks import async_send_fcm_message
                            players_notify = players_list[:10]
                            players_user_id = [player.user.id for player in players_notify]
                            players_list.filter(user__id__in = players_user_id).update(last_notifications = timezone.now())
                            async_send_fcm_message.delay(
                                users_id = players_user_id,
                                title= "🎮 Mesa de Domino Activa",
                                message= f"Hay jugadores esperando para jugar, únete a esta partida en Domino Club."
                            )

            except Exception as error:
                logger.critical(f'Ocurrio una excepcion dentro del automatico de la mesa {game.id} para expulsar un player, error: {str(error)}')
    except DominoGame.DoesNotExist:
        pass 
    except Exception as e:
        logger.critical(f"Error procesando mesa {game_id} en el automatico, error: {str(e)}, time: {(timezone.now() - start_time).total_seconds()} segundos")

def automatic_tournament(tournament_id: int):
    try:
        tournament = Tournament.objects.prefetch_related(
            'player_list__user',           # Para notificaciones a todos los inscritos
            'round_in_tournament',         # Preload de Rondas (related_name en Round)
            'round_in_tournament__game_list', # Preload de juegos dentro de cada ronda
            'round_in_tournament__winner_pair_list__player1__user', # Para premios
            'round_in_tournament__winner_pair_list__player2__user'
        ).get(id=tournament_id)
        now = timezone.now()
        
        player_list = tournament.player_list.all()
        player_in_tournament = player_list.count()
        diff_start = tournament.start_at - timedelta(minutes=5)
        if  diff_start < now and not tournament.notification_5 and int(player_in_tournament) == int(tournament.max_player):
                       
            from dominoapp.tasks import async_send_fcm_message
            # Enviamos UNA tarea para cada mensaje pq depende de la zona horario del player
            timezone_list = player_list.order_by("timezone").distinct("timezone").values_list("timezone", flat=True)
            for player_timezone in timezone_list:
                players_id = player_list.filter(timezone=player_timezone).values_list("user__id", flat=True)
                try:
                    async_send_fcm_message.delay(
                        users_id=list(players_id),
                        title= "⏰ Recordatorio de inicio",
                        message=f"Recordatorio: El torneo comienza en 5 minutos, a las {tournament.start_at.astimezone(pytz.timezone(player_timezone)).strftime('%H:%M')}. ¡Nos vemos pronto en la mesa!"
                    )
                except Exception as error:
                    logger.error(f'Error al enviar notificacion FCM de recordatorio de inicio de torneo" => {str(error)}')
                
            tournament.notification_5 = True
            tournament.save(update_fields=['notification_5'])
            
            TournamentService.process_order_players_rounds(tournament)

        if tournament.start_at < now and tournament.status == 'ready':
            from dominoapp.tasks import async_send_fcm_message
            for game in DominoGame.objects.filter(tournament__id=tournament.id):
                players = game_tools.playersCount(game)
                success = automaticStart(game, players)
                if success:
                    try:
                        send_ws_notification(
                            game_id= game.id,
                            payload={
                                "a": WSActions.GAME_STARTED,
                                "d": {
                                    "st": game.status
                                } 
                            }
                        )
                    except Exception as error:
                        logger.error(f"Error enviando el ws en el Start automatico del torneo. Error: {error}")
                # Agrupamos los jugadores de ESTA mesa
                game_user_ids = [p.user.id for p in players]
                try:
                    async_send_fcm_message.delay(
                        users_id=game_user_ids,
                        title="🏆 Torneo Iniciado",
                        message="Entra ya, no te lo pierdas"
                    )
                except Exception as error:
                    logger.error(f'Error al enviar notificacion FCM de inicio de torneo" => {str(error)}')
            
            tournament.status = "ru"
            tournament.save(update_fields=["status"])

        if tournament.status == 'ru':
            last_round = Round.objects.filter(tournament__id = tournament.id).order_by("-round_no").first()
            if last_round.status == 'ready' and last_round.start_at + timedelta(seconds=30) < now:
                from dominoapp.tasks import async_send_fcm_message
                for game in last_round.game_list.all():
                    if game.status == 'ready':
                        players = game_tools.playersCount(game)
                        success = automaticStart(game, players)
                        if success:
                            try:
                                send_ws_notification(
                                    game_id= game.id,
                                    payload={
                                        "a": WSActions.GAME_STARTED,
                                        "d": {
                                            "st": game.status
                                        } 
                                    }
                                )
                            except Exception as error:
                                logger.error(f"Error enviando el ws en el Start automatico del torneo. Error: {error}")

                        # Agrupamos los jugadores de ESTA mesa
                        game_user_ids = [p.user.id for p in players]
                        try:
                            async_send_fcm_message.delay(
                                users_id=game_user_ids,
                                title= "🚨 Ronda Activa 🚨",
                                message= "La nueva ronda ya empezó. ¡Únete ahora o te lo pierdes!"
                            )
                        except Exception as error:
                            logger.error(f'Error al enviar notificacion FCM de ronda activa" => {str(error)}')
            
            last_round = Round.objects.filter(tournament__id = tournament.id).order_by("-round_no").first()
            if last_round.end_at is not None and last_round.end_at + timedelta(minutes=5) < now:
                TournamentService.process_order_players_rounds(tournament, last_round)
            
    except Exception as error:
        logger.critical(f'Ocurrio una excepcion dentro del automatico de los torneos, error: {str(error)}')         

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
        logger.critical(f"Error en la seleccion del salidor automatico en la mesa {game.id}, error: {str(e)}")

def automaticMove(game: DominoGame):
    try:
        MOVE_TILE_TIME = game.moveTime
        time_diff = timezone.now() - lastMove(game)
        if len(game.board) == 0:
            if time_diff.seconds > (MOVE_TILE_TIME + ApiConstants.AUTO_MOVE_WAIT):
                try:
                    with transaction.atomic():
                        try:
                            game_block = (DominoGame.objects
                            .select_for_update(of=('self',), skip_locked=True)
                            .select_related(
                                'player1__user', 'player2__user', 
                                'player3__user', 'player4__user'
                            ).get(id=game.id))
                        except Exception as error:
                            return

                        # 3. Bloqueamos a los jugadores que YA están sentados de forma independiente
                        # Esto evita el error de PostgreSQL
                        player_ids = [pid for pid in [game_block.player1_id, game_block.player2_id, game_block.player3_id, game_block.player4_id] if pid]
                        if player_ids:
                            # Al hacer list() forzamos la ejecución del select_for_update en la DB
                            locked_players  = list(Player.objects.select_for_update(skip_locked=True).filter(id__in=player_ids))
                            
                            if len(locked_players) < len(player_ids):
                                # Alguien más está tocando a un jugador, mejor salir y reintentar en 7 seg
                                return

                        next_idx = game_block.next_player
                        active_players = game_tools.playersCount(game_block)
                        players = [p for p in active_players if p.isPlaying]

                        if next_idx >= len(players):
                            raise Exception(f"Índice {next_idx} fuera de rango para mesa {game_block.id} con {len(players)} jugadores activos.")
                        
                        # Identificamos al jugador que le toca mover (ahora es una instancia segura)
                        player_w = players[next_idx]

                        tile = game_tools.takeRandomTile(player_w.tiles)

                        error, payload = game_tools.movement(game_block, player_w, players, tile, automatic=True)
                        if error is not None:
                            raise Exception(f"Error en el movimiento automático del jugador {player_w.alias} en la mesa {game_block.id} al intentar realizar la salida. Error: {error}")
                        
                        game_tools.updateLastPlayerTime(game_block, player_w.alias)
                        
                        # Registramos la función para que corra SOLO si el commit es exitoso
                        try:
                            transaction.on_commit(lambda: send_ws_notification(
                                game_id= game_block.id,
                                payload= payload
                            ))
                        except Exception as error:
                            logger.error(f"Error al enviar el WS en el movimiento automatico: {error}")
                except Exception as e:
                    logger.critical(f"Error crítico en el movimiento automático en la mesa {game.id} al intentar realizar la salida, error: {str(e)}")            
        else:
            next_idx = game.next_player
            active_players = game_tools.playersCount(game)
            players = [p for p in active_players if p.isPlaying]

            # Identificamos al jugador que le toca mover
            player_w = players[next_idx]
            player_diff_time = timezone.now() - player_w.lastTimeInSystem

            tile = game_tools.takeRandomCorrectTile(player_w.tiles, game.leftValue, game.rightValue)
            if game_tools.isPass(tile):
                if time_diff.seconds > ApiConstants.AUTO_PASS_WAIT:
                    try:
                        with transaction.atomic():
                            try:
                                game_block = (DominoGame.objects
                                .select_for_update(of=('self',), skip_locked=True)
                                .select_related(
                                    'player1__user', 'player2__user', 
                                    'player3__user', 'player4__user'
                                ).get(id=game.id))
                            except Exception as error:
                                return

                            # 3. Bloqueamos a los jugadores que YA están sentados de forma independiente
                            # Esto evita el error de PostgreSQL
                            player_ids = [pid for pid in [game_block.player1_id, game_block.player2_id, game_block.player3_id, game_block.player4_id] if pid]
                            if player_ids:
                                # Al hacer list() forzamos la ejecución del select_for_update en la DB
                                locked_players  = list(Player.objects.select_for_update(skip_locked=True).filter(id__in=player_ids))
                                
                                if len(locked_players) < len(player_ids):
                                    # Alguien más está tocando a un jugador, mejor salir y reintentar en 7 seg
                                    return

                            if next_idx >= len(players):
                                raise Exception(f"Índice {next_idx} fuera de rango para mesa {game_block.id} con {len(players)} jugadores activos.")

                            error, payload = game_tools.movement(game_block, player_w, players, tile, automatic=True)
                            if error is not None:
                                raise Exception(f"Error en el movimiento automático del jugador {player_w.alias} en la mesa {game.id}, error: {str(error)}")
                            
                            game_tools.updateLastPlayerTime(game, player_w.alias)
                            
                            # Registramos la función para que corra SOLO si el commit es exitoso
                            try:
                                transaction.on_commit(lambda: send_ws_notification(
                                    game_id= game_block.id,
                                    payload= payload
                                ))
                            except Exception as error:
                                logger.error(f"Error al enviar el WS en el movimiento automatico: {error}")
                    except Exception as e:
                        logger.critical(f"Error en el movimiento automático del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")
            elif time_diff.seconds > (MOVE_TILE_TIME + ApiConstants.AUTO_MOVE_WAIT) or (player_diff_time.seconds > ApiConstants.WAIT_FOR_PLAYER and time_diff.seconds > ApiConstants.AUTO_MOVE_WAIT):
                try:
                    with transaction.atomic():
                        try:
                            game_block = (DominoGame.objects
                            .select_for_update(of=('self',), skip_locked=True)
                            .select_related(
                                'player1__user', 'player2__user', 
                                'player3__user', 'player4__user'
                            ).get(id=game.id))
                        except Exception as error:
                            return

                        # 3. Bloqueamos a los jugadores que YA están sentados de forma independiente
                        # Esto evita el error de PostgreSQL
                        player_ids = [pid for pid in [game_block.player1_id, game_block.player2_id, game_block.player3_id, game_block.player4_id] if pid]
                        if player_ids:
                            # Al hacer list() forzamos la ejecución del select_for_update en la DB
                            locked_players  = list(Player.objects.select_for_update(skip_locked=True).filter(id__in=player_ids))
                            
                            if len(locked_players) < len(player_ids):
                                # Alguien más está tocando a un jugador, mejor salir y reintentar en 7 seg
                                return

                        if next_idx >= len(players):
                            raise Exception(f"Índice {next_idx} fuera de rango para mesa {game_block.id} con {len(players)} jugadores activos.")

                        error, payload = game_tools.movement(game_block, player_w, players, tile, automatic=True)
                        if error is not None:
                            raise Exception(f"Error en el movimiento automático del jugador {player_w.alias} en la mesa {game.id}, message: {error}")
                        
                        game_tools.updateLastPlayerTime(game_block, player_w.alias)
                        
                        # Registramos la función para que corra SOLO si el commit es exitoso
                        try:
                            transaction.on_commit(lambda: send_ws_notification(
                                game_id= game_block.id,
                                payload= payload
                            ))
                        except Exception as error:
                            logger.error(f"Error al enviar el WS en el movimiento automatico: {error}")
                except Exception as e:
                    logger.critical(f"Error en el movimiento automático del jugador {player_w.alias} en la mesa {game.id}, error: {str(e)}")   
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
                return False
            else:
                game_tools.startGame1(game, blocked_players)
                return True

        except Exception as error:
            logger.critical(f"Error en el reinicio automático de la mesa {game.id}, error: {str(error)}")
            return False
    return False