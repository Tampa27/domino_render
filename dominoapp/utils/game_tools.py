from rest_framework.response import Response
from dominoapp.models import Player, SummaryPlayer, DominoGame, MoveRegister,Bank, Match_Game
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import DatabaseError
from django.db.models import F
import random
from django.db import transaction
import logging
from dominoapp.utils.transactions import create_game_transactions
from dominoapp.connectors.pusher_connector import PushNotificationConnector
from dominoapp.utils.constants import ApiConstants
from dominoapp.utils.cache_tools import update_player_presence_cache
from dominoapp.utils.players_tools import update_elo_pair, update_elo, get_summary_model

logger = logging.getLogger(__name__)
logger_discord = logging.getLogger('django')


def setWinner1(game: DominoGame, winner: int):
    game.winner = winner
    game.start_time = timezone.now()

def setWinnerStarterNext1(game: DominoGame, winner: int, starter: int, next_player: int):
    game.starter = starter
    game.winner = winner
    game.next_player = next_player
    game.start_time = timezone.now()

def checkPlayerJoined(player: Player,game: DominoGame) -> tuple[bool, list[Player]]:
    res = False
    players = []
    if game.player1 is not None:
        players.append(game.player1)
        if game.player1.alias == player.alias:
            res = True
    if game.player2 is not None:
        players.append(game.player2)
        if game.player2.alias == player.alias:
            res = True
    if game.player3 is not None:
        players.append(game.player3)
        if game.player3.alias == player.alias:
            res = True
    if game.player4 is not None:
        players.append(game.player4)
        if game.player4.alias == player.alias:
            res = True
    return res,players

def startGame1(game: DominoGame, players: list[Player]):
    start_time = timezone.now()
    n = len(players)
    try:
        # 1. Lógica de starter y next_player (sin cambios, pero más compacta)
        if game.starter == -1 or game.starter >= n:
            game.next_player = random.randint(0, n-1)
            game.starter = game.next_player
        else:
            game.next_player = game.starter
        
        # 2. Lógica de ganador en modo parejas
        if game.inPairs and game.winner != DominoGame.Tie_Game:
            game.winner = DominoGame.Winner_Couple_1 if game.starter in (0, 2) else DominoGame.Winner_Couple_2
        
        # 3. Resetear estado del juego
        game.board = ''
        game.leftValue = -1
        game.rightValue = -1
        game.lastTime1 = game.lastTime2 = game.lastTime3 = game.lastTime4 = timezone.now()
        
        bank_data = {
            'data_played': 1
        }        
        
        # 6. Lógica de puntos y contadores de juegos completados
        if game.perPoints and game.status in ("ready", "fg"):
            game.scoreTeam1 = 0
            game.scoreTeam2 = 0
            game.rounds = 0
            
            # Resetear puntos de jugadores en memoria (sin DB)
            for player in players:
                player.points = 0
            
            bank_data['game_played'] = 1
        elif not game.perPoints:
            bank_data['game_played'] = 1
                
        # 8. Repartir fichas y actualizar estado
        shuffle(game, players)
        game.status = "ru"
        game.start_time = timezone.now()
        
        # 9. Guardar juego con todos los campos actualizados en una sola query
        game.save(update_fields=[
            'board', 'status', 'start_time', 'leftValue', 'rightValue',
            'lastTime1', 'lastTime2', 'lastTime3', 'lastTime4',
            'next_player', 'starter', 'winner', 'scoreTeam1', 'scoreTeam2', 'rounds'
        ])

        # 10. Actualizar estadísticas del banco de forma asíncrona
        try:
            from dominoapp.tasks import async_update_summarys
            async_update_summarys.delay(bank_update_data=bank_data)
        except Exception as e:
            logger_discord.error(f"Error lanzando async_update_summarys para banco en startGame1: {e}")

    except Exception as e:
        logger_discord.critical(f"Error crítico en startGame1, Error: {str(e)}, time: {(timezone.now() - start_time).total_seconds()} segundos")

def movement(game: DominoGame, player: Player, players: list[Player], tile: str, automatic=False):
    n = len(players)
    w = getPlayerIndex(players, player)
    passTile = isPass(tile)
    
    # 1. Validaciones iniciales (Fail Fast)
    error = validate_move(game, player, players, tile, w, passTile)
    if error:
        return error

    # --- PREPARACIÓN DE DATOS ASÍNCRONOS ---
    bank_data = {'game_coins': 0}
    player_data_list = [{'id': p.id, 'summary_fields': {}, 'transaction': None} for p in players]
    
    # Datos para el MoveRegister (que ahora será asíncrono)
    move_data = {
        'game_id': game.id,
        'player_id': player.id,
        'tile': tile,
        'automatic': automatic,
        'players_id': [p.id for p in players]
    }

    if not passTile:
        isCapicua = False
        if game.perPoints:
            isCapicua = checkCapicua(game, tile)
        
        updateSides(game, tile)
        tiles_count, new_tiles = updateTiles(player, tile)
        player.tiles = new_tiles
        player.save(update_fields=['tiles'])

        if tiles_count == 0:
            handle_game_win(game, players, w, n, bank_data, player_data_list, isCapicua)
        else:
            game.next_player = (w + 1) % n          
    elif checkClosedGame1(game, n):
        winner = getWinner(players, game.inPairs, game.variant)
        handle_closed_game(game, players, winner, n, bank_data, player_data_list)
    else:
        # Es un pase normal
        updatePassCoins(w, game, players, player_data_list)
        game.next_player = (w + 1) % n

    # 4. Guardado final de la mesa (Una sola query)
    game.board += (tile + ',')
    game.save(update_fields=[
        'board', 'status', 'next_player', 'starter', 'winner', 
        'leftValue', 'rightValue', 'rounds', 'start_time', 
        'scoreTeam1', 'scoreTeam2'
    ])
    
    if game.status in ["fg", "fi"]:
        prepare_summary_end_game(game, players, bank_data, player_data_list)
    
    # --- LANZAR TAREA ASÍNCRONA ---
    # Enviamos todo el paquete de datos para que Celery trabaje
    try:
        from dominoapp.tasks import async_update_summarys
        transaction.on_commit(lambda: async_update_summarys.delay(
            game.id, 
            player_data_list, 
            bank_data, 
            move_data
        ))
    except Exception as e:
        logger_discord.error(f"Error lanzando async_update_summarys para game {game.id}: {e}")

    logger.info(f"{player.alias} movio {tile}")
    return None

#### Adicionales para limpieza en el movement ####
def validate_move(game: DominoGame, player: Player, players: list[Player], tile:str, player_position:int, passTile: bool):
    """Valida el movimiento de un jugador. """
    n = len(players)
    if isMyTurn(player_position, game.next_player) == False:
        logger.warning(f"{player.alias} intento mover {tile} pero se detecto que no es su turno. Esta en la posicion: {player_position} y le toca el turno al player: {game.next_player}. El salidor es {game.starter}")
        return(f"{player.alias} intento mover {tile} pero se detecto que no es su turno. Esta en la posicion: {player_position} y le toca el turno al player: {game.next_player}. El salidor es {game.starter}")
    if noCorrect(game,tile):
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que no es una ficha correcta")
        return(f"{player.alias} intento mover {tile} pero se detecto que no es una ficha correcta")
    if (passTile and (game.status == 'fi' or game.status == 'fg')):
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que el juego habia terminado")
        return(f"{player.alias} intento mover {tile} pero se detecto que el juego habia terminado")
    if (len(game.board) == 0 and passTile):
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que el juego habia empezado")
        return(f"{player.alias} intento mover {tile} pero se detecto que el juego habia empezado")
    if CheckPlayerTile(tile, player) == False:
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que la ficha no le pertenese")
        return(f"{player.alias} intento mover {tile} pero se detecto que la ficha no le pertenese")
    if not CorrectPassTile(game,player,tile):
        logger.warning(player.alias+" intento mover "+tile +" pero se detecto que tenia fichas para jugar")
        return(f"{player.alias} intento pasarse con fichas")
    
    return None

def prepare_summary_end_game(game: DominoGame, players: list[Player], bank_data: dict, player_data_list: list[dict]):
    """Prepara las estadísticas de todos los jugadores y el banco en bloque."""
    player_ids = [p.id for p in players]
    
    # Actualización del Banco
    bank_data['data_completed'] = 1
    if game.status == "fg":
        bank_data['game_completed'] = 1

    
    # Determinamos los sufijos de los campos según la variante
    variant_field = 'play_66_game' if game.variant == 'd6' else 'play_99_game'
    pair_field = 'play_in_pairs' if game.inPairs else 'play_in_single'
    points_field = 'play_by_points' if game.perPoints else 'play_without_points'

    for i, player in enumerate(players):
        # Buscamos el diccionario del jugador en la lista ya existente
        p_data = next((d for d in player_data_list if d['id'] == player.id), None)
        if not p_data: continue

        if game.status == "fg":
            # Añadimos los incrementos de estadísticas
            summ = p_data.setdefault('summary_fields', {})
            summ[variant_field] = summ.get(variant_field, 0) + 1
            summ[pair_field] = summ.get(pair_field, 0) + 1
            summ[points_field] = summ.get(points_field, 0) + 1

        if game.winner == DominoGame.Tie_Game:
            summ['data_tie'] = summ.get('data_tie', 0) + 1

def handle_game_win(game: DominoGame, players: list[Player], winner_idx: int, n: int, bank_data: dict, player_data_list: list[dict], isCapicua: bool):
    """Maneja la victoria por quedarse sin fichas."""
    game.status = 'fg'
    game.start_time = timezone.now()
    game.winner = winner_idx

    # Lógica de rotación de salida (Starter)
    if game.startWinner:
        game.starter = winner_idx
        game.next_player = winner_idx
    else:
        game.starter = (game.starter + 1) % n
        game.next_player = game.starter

    if game.perPoints:
        game.rounds += 1
        # Actualización atómica de Match_Game si aplica
        if game.in_tournament:
            Match_Game.objects.filter(game__id=game.id).update(count_game=F('count_game') + 1)
        
        # Llamamos a la función de puntos que optimizamos antes
        updateAllPoints(game, players, winner_idx, bank_data, player_data_list, isCapicua)
    else:
        # Si no es por puntos, solo actualizamos los datos básicos
        updatePlayersData(game, players, winner_idx, "fg", bank_data, player_data_list)
        
        # Mapeo de ganador a pareja si es necesario
        if game.inPairs:
            if winner_idx in [0, 2]:
                game.winner = DominoGame.Winner_Couple_1
            else:
                game.winner = DominoGame.Winner_Couple_2

def handle_closed_game(game: DominoGame, players: list[Player], winner: int, n: int, bank_data: dict, player_data_list: list[dict]):
    """Maneja la lógica cuando el juego se cierra/tranca."""
    game.status = 'fg'
    game.start_time = timezone.now()
    game.winner = winner

    if winner < DominoGame.Tie_Game: # Alguien ganó   
        # Rotación de salida
        if game.startWinner:
            game.starter = winner
            game.next_player = winner
        else:
            game.starter = (game.starter + 1) % n
            game.next_player = game.starter        

    if game.perPoints:
        game.rounds += 1
        if game.in_tournament:
            Match_Game.objects.filter(game__id=game.id).update(count_game=F('count_game') + 1)
            
        if winner < DominoGame.Tie_Game: # Alguien ganó por puntos            
            updateAllPoints(game, players, winner, bank_data, player_data_list) 
        elif winner == DominoGame.Tie_Game: # Empate técnico
            game.status = "fi" # El juego sigue o se repite la mano según tu regla
            # Lógica de quién sale en el empate
            if not (game.startWinner and (game.lostStartInTie != True or game.inPairs == False)):
                game.starter = (game.starter + 1) % n
            game.next_player = game.starter
    else:
        # Juego cerrado sin puntos
        updatePlayersData(game, players, winner, "fg", bank_data, player_data_list)
        if game.inPairs and winner < DominoGame.Tie_Game:
            game.winner = DominoGame.Winner_Couple_1 if winner in [0, 2] else DominoGame.Winner_Couple_2

#################################################################
def CheckPlayerTile(tile:str, player:Player):
    if isPass(tile):        
        return True
    tiles = player.tiles.split(',')
    inverse = rTile(tile)
    if tile in tiles or inverse in tiles:
        return True
    return False

def CorrectPassTile(game: DominoGame, player:Player, tile:str):
    tiles = player.tiles.split(',')
    if isPass(tile):        
        numbers = [int(side) for single in tiles for side in single.split('|')]
        if game.leftValue in numbers or game.rightValue in numbers:
            # Comprobar que realmente no lleva fichas
            return False
    return True 

def noCorrect(game,tile):
    values = tile.split('|')
    val0 = int(values[0])
    if val0 == -1 or (game.leftValue == -1 and game.rightValue == -1):
        return False
    if game.leftValue == val0 or game.rightValue == val0:
        return False
    return True

def rTile(tile)->str:
    values = tile.split('|')
    return (values[1]+"|"+values[0])

def updatePlayersData(game: DominoGame, players: list[Player], w: int, status: str, bank_data: dict, player_data_list: list[dict]):
    
    n = len(players)
    playing_count = sum(1 for p in players if p.isPlaying)
    is_final_game = (status == "fg")
    
    # Listas para guardar cambios y procesar al final
    players_to_update = []
    
    # 2. Identificar ganadores según el modo
    winners_idx = []
    if game.inPairs:
        if w < 4: winners_idx = [w, (w + 2) % 4]
    else:
        if w < n: winners_idx = [w]

    # 3. Bucle único de cálculo (CPU es más barato que DB)
    for i in range(n):
        player = players[i]
        if not player: continue
        p_data = next((d for d in player_data_list if d['id'] == player.id), None)
        
        is_winner = i in winners_idx        
        # Valores de pago
        win_val = game.payWinValue
        match_val = game.payMatchValue if (is_final_game and game.perPoints) else 0
        
        summ = p_data.setdefault('summary_fields', {})

        if is_winner:
            # Lógica Ganador
            summ['data_wins'] = summ.get('data_wins', 0) + 1
            if is_final_game and game.perPoints:
                summ['match_wins'] = summ.get('match_wins', 0) + 1
            
            # Cálculo de monedas (Individual vs Parejas)
            multiplier = (playing_count - 1) if not game.inPairs else 1
            total_win = (win_val * multiplier) + (match_val * multiplier)
            
            if total_win > 0:
                fee_percent = ApiConstants.DISCOUNT_PERCENT / 100
                bank_fee = int(total_win * fee_percent)
                player_net = total_win - bank_fee
                
                bank_data['game_coins'] = bank_data.get('game_coins', 0) + bank_fee
                player.earned_coins += player_net
                summ['earned_coins'] = summ.get('earned_coins', 0) + player_net
                
                # Transacción única por premio total
                p_data['transaction'] = {
                    'to_user': True, 
                    'amount': player_net,
                    'description': f"Gané game {game.id}"
                }
        else:
            # Lógica Perdedor (Solo si el ganador es válido w < 4)
            if w < 4 and player.isPlaying:
                summ['data_loss'] = summ.get('data_loss', 0) + 1
                if is_final_game and game.perPoints:
                    summ['match_loss'] = summ.get('match_loss', 0) + 1
                
                total_loss = win_val + match_val
                if total_loss > 0:
                    player.earned_coins -= total_loss
                    if player.earned_coins < 0:
                        player.recharged_coins += player.earned_coins
                        player.earned_coins = 0
                    
                    summ['loss_coins'] = summ.get('loss_coins', 0) + total_loss
                    p_data['transaction'] = {
                        'from_user': True,
                        'amount': total_loss,
                        'description': f"Perdí game {game.id}"
                    }

        # Añadir a colas de guardado
        players_to_update.append(player)

    # 4. PERSISTENCIA MASIVA (El gran ahorro de tiempo)
    for p in players_to_update:
        p.save(update_fields=['earned_coins', 'recharged_coins'])
    
    # 5. Actualización de ELO (al final de la transacción)
    if is_final_game:
        try:
            if game.inPairs:
                update_elo_pair([players[0], players[2]], [players[1], players[3]], (w >= 4))
            else:
                update_elo(players, (players[w] if w < 4 else None))
        except Exception as e:
            logger_discord.error(f"Error actualizando ELO game {game.id}: {e}")

def updatePassCoins(pos: int, game: DominoGame, players: list[Player], player_data_list: list[dict]):
    if game.payPassValue <= 0:
        return # Si no hay pago por pase, ahorramos todo el procesamiento

    tiles = game.board.split(',')
    rtiles = reversed(tiles)
    prev = 1
    n = len(players)
    
    pos1 = -1 # Posición del jugador que "dio el pase"

    # 1. Lógica de búsqueda de quién pasó a quién
    for tile in rtiles:
        if not tile: continue
        if isPass(tile):
            prev += 1
        else:
            # Determinamos pos1 basándonos en la distancia (prev)
            if prev in [1, 3] or (prev == 2 and not game.inPairs):
                pos1 = (pos - prev) % n
            break # Encontramos el movimiento anterior, salimos del bucle

    # 2. Si identificamos un pase válido, procesamos en bloque
    if pos1 != -1:
        player_pass = players[pos]       # El que se pasó
        player_passed = players[pos1]    # El que hizo que el otro se pasara
        
        loss_coins = game.payPassValue
        bank_coins = 0 # Mantengo tu lógica de bank_coins=0
        coins_to_receive = loss_coins - bank_coins

        # 3. Actualización de saldos en memoria
        player_pass.earned_coins -= loss_coins
        if player_pass.earned_coins < 0:
            player_pass.recharged_coins += player_pass.earned_coins
            player_pass.earned_coins = 0
        
        player_passed.earned_coins += coins_to_receive

        # Actualización de estadísticas en memoria
        summ_pass = player_data_list[pos].setdefault('summary_fields', {})
        summ_passed = player_data_list[pos1].setdefault('summary_fields', {})
        summ_pass['loss_coins'] = summ_pass.get('loss_coins', 0) + loss_coins
        summ_pass['owner_pass'] = summ_pass.get('owner_pass', 0) + 1
        summ_passed['earned_coins'] = summ_passed.get('earned_coins', 0) + coins_to_receive
        summ_passed['pass_player'] = summ_passed.get('pass_player', 0) + 1

        # 5. PERSISTENCIA ÚNICA (Aquí es donde ganamos velocidad)
        # Usamos save() una sola vez por objeto con update_fields
        player_pass.save(update_fields=['earned_coins', 'recharged_coins'])
        player_passed.save(update_fields=['earned_coins'])
        
        # 6. Transacciones (Ojalá pudieras hacer esto asíncrono)
        descriptions_pass = f"{player_passed.alias} me paso en el juego {game.id}, a {game.leftValue} y a {game.rightValue}"
        descriptions_passed = f"pase a {player_pass.alias} en el juego {game.id}, a {game.leftValue} y a {game.rightValue}"
        
        player_data_list[pos]['transaction'] = {
            'from_user':True, 
            'amount':loss_coins,
            'description':descriptions_pass
            }
        player_data_list[pos1]['transaction'] = {
            'to_user':True,
            'amount':coins_to_receive,
            'description':descriptions_passed
        }

def move1(game_id: int, player_request: Player, tile: str):
    start_time = timezone.now()
    try:
        with transaction.atomic():
            # 1. Bloqueamos la mesa y traemos los datos de los jugadores en un JOIN
            try:
                game = DominoGame.objects.select_related(
                    'player1', 'player2', 'player3', 'player4'
                ).select_for_update(of=('self',), nowait=True).get(id=game_id)
            except DominoGame.DoesNotExist:
                return "Mesa no encontrada."

            # 2. Creamos una lista que mantiene EL ORDEN DE LA MESA (para tu lógica)
            # Estos objetos ya vienen con datos por el select_related
            ordered_players_in_table = [game.player1, game.player2, game.player3, game.player4]

            # 3. Extraemos IDs de jugadores existentes para el BLOQUEO
            player_ids = [p.id for p in ordered_players_in_table if p is not None]
            
            # 4. ORDENAMOS LOS IDS SOLO PARA EL SELECT_FOR_UPDATE
            # Esto previene Deadlocks y no afecta a 'game.player1', 'game.player2', etc.
            ids_to_lock = sorted(player_ids)

            # Bloqueamos en la DB usando el orden numérico de ID
            locked_players  = list(Player.objects.select_for_update(nowait=True).filter(id__in=ids_to_lock))
            if len(locked_players) < len(player_ids):
                # Alguien más está tocando a un jugador, mejor salir y reintentar mas tarde
                return "No se pudieron bloquear a todos los jugadores"

            # 5. Buscamos al jugador que realiza el movimiento
            # Lo buscamos en la lista original (la que tiene el orden de la mesa)
            player = next((p for p in ordered_players_in_table if p and p.id == player_request.id), None)
            if not player:
                return "Jugador no encontrado en esta partida"

            # 6. Preparamos la lista de jugadores activos (isPlaying) manteniendo el orden
            players_ru = [p for p in ordered_players_in_table if p and p.isPlaying]
            
            # 7. Ejecutamos la lógica (aquí game.player1, player2, etc. siguen siendo los correctos)
            error = movement(game, player, players_ru, tile)
            
            if error is None:
                # Actualizamos tiempos sin volver a guardar todo el objeto si no es necesario
                updateLastPlayerTime(game, player.alias)
                
                # IMPORTANTE: Solo guardamos los campos que realmente cambian para evitar sobreescribir
                # datos que otros procesos podrían estar tocando.
                game.save(update_fields=[
                    'lastTime1', 'lastTime2', 'lastTime3', 'lastTime4'
                ])

                #### esto hay que cambiarlo a asincrono y pasarcelo a Celery para que no afecte el rendimiento del movimiento, lo mismo con el update_player_presence_cache
                now = timezone.now()
                if player.lastTimeInSystem + timedelta(seconds = 5) < now:
                    player.inactive_player = False
                    player.lastTimeInSystem = now
                    player.lastTimeInGame = now
                    player.save(update_fields=["inactive_player", "lastTimeInSystem" , "lastTimeInGame"])
                    data={
                            'lastTimeInSystem': now,
                            'lastTimeInGame' : now
                        }
                    update_player_presence_cache(player.id, data)
                ###########################################################
            return error

    except DatabaseError:
        return "La partida está procesando otro movimiento. Intenta de nuevo."
    except Exception as e:
        logger_discord.critical(f"Error crítico en move1, Error: {str(e)}, time: {(timezone.now() - start_time).total_seconds()} segundos")
        return "Error al procesar el request del movimiento."

def shuffleCouples(game,players):
    random.shuffle(players)
    game.player1 = players[0]
    game.player2 = players[1]
    game.player3 = players[2]
    game.player4 = players[3]

def exitPlayer(game: DominoGame, player: Player, players: list[Player], totalPlayers: int):
    # 1. Identificar posición de forma rápida
    pos = getPlayerIndex(players, player)
    if pos == -1:
        return False

    isStarter = (game.starter == pos)
    starter_original = game.starter
    
    # 2. Determinar inactividad (Fast Check)
    lastTimeMove = getLastMoveTime(game, player)
    noActivity = False
    if lastTimeMove:
        if (timezone.now() - lastTimeMove).total_seconds() >= 60:
            noActivity = True

    # 3. Quitar al jugador de la ranura de la mesa (Memory only por ahora)
    if game.player1_id == player.id: game.player1 = None
    elif game.player2_id == player.id: game.player2 = None
    elif game.player3_id == player.id: game.player3 = None
    elif game.player4_id == player.id: game.player4 = None

    # 4. Lógica de Penalización (Solo si el juego está en curso y no es por inactividad)
    if player.isPlaying:
        player.isPlaying = False # Marcar como ya no jugando
        have_points = havepoints(game)
        
        # ¿Debe pagar por abandonar?
        game_in_progress = (game.status == "fi" or (game.status == "ru" and (have_points or game.board != "")))
        should_pay = game_in_progress and (game.payWinValue > 0 or game.payMatchValue > 0) and not noActivity

        if should_pay:
            loss_coins = (game.payWinValue + game.payMatchValue)
            fee_percent = ApiConstants.DISCOUNT_PERCENT / 100
            bank_fee = int(loss_coins * fee_percent)
            net_to_distribute = loss_coins - bank_fee

            # Actualizar Banco
            try:
                bank = Bank.objects.first()
            except ObjectDoesNotExist:
                bank = Bank.objects.create()
            bank.game_coins += bank_fee
            bank.save(update_fields=['game_coins'])

            # Distribuir monedas a los que se quedan
            if game.inPairs:
                share = int(net_to_distribute / 2)
                players[(pos+1)%4].earned_coins+=share
                summary_player = get_summary_model(players[(pos+1)%4])
                summary_player.earned_coins += share
                summary_player.save(update_fields=['earned_coins'])
                create_game_transactions(
                    game=game, to_user=players[(pos+1)%4], amount=share, status="cp",
                    descriptions=f"{player.alias} salio del juego {game.id}")
                players[(pos+3)%4].earned_coins+=share
                create_game_transactions(
                    game=game, to_user=players[(pos+3)%4], amount=share, status="cp",
                    descriptions=f"{player.alias} salio del juego {game.id}")
                summary_player = get_summary_model(players[(pos+3)%4])
                summary_player.earned_coins += share
                summary_player.save(update_fields=['earned_coins'])
                players[(pos+1)%4].save(update_fields=['earned_coins'])
                players[(pos+3)%4].save(update_fields=['earned_coins'])
            else:
                remaining_players = [p for p in players if p.id != player.id and p.isPlaying]
                if remaining_players:
                    share = int(net_to_distribute / len(remaining_players))
                    for p in remaining_players:
                        p.earned_coins += share
                        p.save(update_fields=['earned_coins'])
                        # Actualizar summary del que recibe
                        summary = get_summary_model(p)
                        summary.earned_coins += share
                        summary.save(update_fields=['earned_coins'])
                        create_game_transactions(game=game, to_user=p, amount=share, status="cp", descriptions=f"{player.alias} salió")

            # Penalizar al que salió
            player.earned_coins -= loss_coins
            if player.earned_coins < 0:
                player.recharged_coins += player.earned_coins
                player.earned_coins = 0
            summary = get_summary_model(player)
            summary.loss_coins += loss_coins
            summary.save(update_fields=['loss_coins'])
            create_game_transactions(game=game, from_user=player, amount=loss_coins, status="cp", descriptions="por salir del juego")

        # 5. Actualizar estado del juego tras la salida
        if totalPlayers <= 2 or game.inPairs:
            game.status = "wt"
            game.starter = -1
            game.board = ""
        elif (totalPlayers > 2 and not game.inPairs and game.perPoints) or game.status == "ru":
            game.status = "ready"
            game.starter = -1
        elif totalPlayers > 2 and not game.inPairs and game.status == "fg":
            # Ajustar índices si el que salió estaba antes que el salidor/ganador
            if isStarter and game.startWinner:
                game.starter = -1
            elif not isStarter and game.starter > pos:
                game.starter -= 1
            
            if game.winner < DominoGame.Tie_Game and game.winner > pos:
                game.winner -= 1
    else:
        if totalPlayers <= 2 or game.inPairs:
            game.status = "wt"
            game.starter = -1
            game.board = ""

    # 6. Reordenar y Persistir
    reorderPlayers(game, player, players, starter_original)
    
    now = timezone.now()
    player.points = 0
    player.tiles = ""
    player.lastTimeInGame = now
    player.lastTimeInSystem = now
    
    # Guardado final de objetos
    player.save(update_fields=['points', 'tiles', 'isPlaying', 'earned_coins', 'recharged_coins', 'lastTimeInGame', 'lastTimeInSystem'])
    game.save(update_fields=['player1', 'player2', 'player3', 'player4', 'status', 'starter', 'winner', 'board'])
    
    return True

def reorderPlayers(game: DominoGame, player_who_left: Player, players: list[Player], starter_idx: int):
    """
    Reordena los slots de la mesa (player1-4) tras una salida.
    Optimizado para usar IDs y asignación directa.
    """
    # 1. Filtrar la lista de jugadores en memoria (excluyendo al que salió)
    # Esto mantiene el orden relativo original de los que se quedan
    remaining = [p for p in players if p.id != player_who_left.id]
    
    # 2. Resetear todos los slots (Operación rápida en memoria)
    game.player1 = remaining[0] if len(remaining) > 0 else None
    game.player2 = remaining[1] if len(remaining) > 1 else None
    game.player3 = remaining[2] if len(remaining) > 2 else None
    game.player4 = remaining[3] if len(remaining) > 3 else None

    # 3. Actualizar el starter index
    # Si el que salió era el starter, se invalida (-1)
    # Si no, se ajusta el índice si el starter estaba después del que salió
    if starter_idx == -1:
        game.starter = -1
    else:
        # Buscamos la posición original del jugador que salió para comparar
        # Nota: 'players' es la lista original antes de la salida
        left_idx = -1
        for i, p in enumerate(players):
            if p.id == player_who_left.id:
                left_idx = i
                break
        
        if starter_idx == left_idx:
            game.starter = -1
        elif starter_idx > left_idx:
            game.starter = starter_idx - 1
        else:
            game.starter = starter_idx

def updateTeamScore(game: DominoGame, winner: int, players: list[Player], sum_points: int, bank_data: dict, player_data_list: list[dict]):
    # 1. Determinar equipo ganador y jugadores a actualizar
    # Asumimos: Equipo 1 (índices 0, 2), Equipo 2 (índices 1, 3)
    is_team_1 = winner in [DominoGame.Winner_Player_1, DominoGame.Winner_Player_3]
    team_indices = [0, 2] if is_team_1 else [1, 3]
    
    # Actualizamos los objetos en memoria por si se usan después en esta misma función
    for i in team_indices:
        players[i].points += sum_points
        players[i].save(update_fields=['points'])

    # 3. Actualizar score del juego en memoria
    if is_team_1:
        game.scoreTeam1 += sum_points
    else:
        game.scoreTeam2 += sum_points

    # 4. Lógica de finalización de juego
    if game.scoreTeam1 >= game.maxScore or game.scoreTeam2 >= game.maxScore:
        game.status = "fg"
        game.start_time = timezone.now()
        game.winner = DominoGame.Winner_Couple_1 if game.scoreTeam1 >= game.maxScore else DominoGame.Winner_Couple_2
        
        # Optimización de Torneo: Update directo sin traer el objeto a memoria
        if game.in_tournament:
            field_to_inc = "games_win_team_1" if game.scoreTeam1 >= game.maxScore else "games_win_team_2"
            Match_Game.objects.filter(game__id=game.id).update(**{field_to_inc: F(field_to_inc) + 1})
    else:
        game.status = "fi"
    
    updatePlayersData(game, players, winner, game.status, bank_data, player_data_list)

    # Nota: Asegúrate de que el objeto 'game' se guarde después de llamar a esta función 
    # o añade game.save() aquí si es necesario.

def updateAllPoints(game: DominoGame, players: list[Player], winner: int, bank_data: dict, player_data_list: list[dict], isCapicua=False):
    # 1. Cálculo de puntos base usando comprensión de listas (más rápido)
    all_tiles_points = [totalPoints(p.tiles) for p in players]
    
    if game.sumAllPoints:
        sum_points = sum(all_tiles_points)
    else:
        # Sumar todos excepto el ganador
        sum_points = sum(all_tiles_points) - all_tiles_points[winner]
        # Si es por parejas, también restamos los puntos del compañero
        if game.inPairs:
            partner_idx = (winner + 2) % 4
            sum_points -= all_tiles_points[partner_idx]

    # 2. Aplicar multiplicador de Capicua una sola vez
    if isCapicua and game.capicua:
        sum_points *= 2

    # 3. Delegar o ejecutar la actualización
    if game.inPairs:
        # Reutilizamos la función optimizada anterior
        updateTeamScore(game, winner, players, sum_points, bank_data, player_data_list)
    else:
        # Actualización atómica del jugador individual
        winner_player = players[winner]
        winner_player.points += sum_points
        winner_player.save(update_fields=['points'])
        
        # Determinar estado final
        is_final_game = winner_player.points >= game.maxScore
        game.status = "fg" if is_final_game else "fi"
        
        # Llamada única a updatePlayersData
        updatePlayersData(game, players, winner, game.status, bank_data, player_data_list)

    # Nota: El objeto 'game' debe guardarse al final del proceso principal

def getPlayerIndex(players: list[Player],player: Player):
    for i in range(len(players)):
        if player.id == players[i].id:
            return i
    return -1

def updateSides(game:DominoGame,tile:str):
    values = tile.split('|')
    value1 = int(values[0])
    value2 = int(values[1])
    if len(game.board) == 0:
        game.leftValue = value1
        game.rightValue = value2
    else:    
        if value1 == game.leftValue:
            game.leftValue = value2
        else:
            game.rightValue = value2    

def updateTiles(player:Player,tile:str):
    tiles = player.tiles.split(',')

    inverse = rTile(tile)
    res = ''
    for s in tiles:
        if tile == s:
            tiles.remove(tile)
        elif inverse == s:
            tiles.remove(inverse)

    for i in range(len(tiles)):
        res+=tiles[i]
        if i < (len(tiles)-1):
            res+=','        
    return len(tiles),res

def getWinner(players,inPairs,variant):
    i = 0
    min = 1000
    res = -1
    points = []
    for player in players:
        pts = totalPoints(player.tiles)
        points.append(pts)
        if pts < min:
            min = pts
            res = i
        elif pts == min:
            res = 4
        i+=1
    if variant == "d6" and inPairs:
        sum1 = points[0]+points[2]
        sum2 = points[1]+points[3]
        if sum1 < sum2:
            if points[0] < points[2]:
                return DominoGame.Winner_Player_1
            else:
                return DominoGame.Winner_Player_3
        elif sum1 > sum2:
            if points[1] < points[3]:
                return DominoGame.Winner_Player_2
            else:
                return DominoGame.Winner_Player_4
        else:
            return DominoGame.Tie_Game        
    elif res == DominoGame.Tie_Game and inPairs:
        if points[0] == points[2] and points[2] == min and points[1] != min and points[3] != min:
            res = DominoGame.Winner_Player_1
        elif points[1] == points[3] and points[1] == min and points[0] != min and points[2] != min:
            res = DominoGame.Winner_Player_2         
    return res

def totalPoints(tiles):
    if len(tiles) == 0:
        return 0
    total = 0
    list_tiles = tiles.split(',')
    for tile in list_tiles:
        total+=getPoints(tile)
    return total

def getPoints(tile):
    values = tile.split('|')
    return int(values[0])+int(values[1])    

def checkClosedGame1(game:DominoGame, playersCount: int):
    tiles = game.board.split(',')
    lastPasses = 0
    rtiles = reversed(tiles)
    for tile in rtiles:
        if len(tile) > 0:
            if(isPass(tile)):
                lastPasses+=1
                if lastPasses == playersCount-1:
                    return True
            else:
                return False    
    return False
   
def isPass(tile):
    values = tile.split('|')
    return values[0] == "-1"

def playersCount(game: DominoGame)-> list[Player]:
    players = []
    if game.player1 is not None:
        players.append(game.player1)
    if game.player2 is not None:
        players.append(game.player2)
    if game.player3 is not None:
        players.append(game.player3)
    if game.player4 is not None:
        players.append(game.player4)
    return players

def shuffle(game:DominoGame, players:list[Player]):
    tiles = []
    max = 0
    if game.variant == "d6":
        max = 7
    else:
        max = 10

    for i in range(max):
        for j in range(i,max):
            tiles.append(str(j)+"|"+str(i))
    
    random.shuffle(tiles)

    for i in range(len(players)):
        player = players[i]
        player.tiles = ""
        if game.status !="fi":
            player.isPlaying = True
        if game.perPoints and (game.status =="ready" or game.status =="fg"):
            player.points = 0  
        for j in range(max):
            player.tiles+=tiles[i*max+j]
            if j < (max-1):
                player.tiles+=","
        player.save(update_fields=['tiles','isPlaying','points'])    
    
def checkCapicua(game,tile):
    if game.leftValue == game.rightValue:
        return False
    values = tile.split('|')
    val1 = int(values[0])
    val2 = int(values[1])
    return (val1 == game.leftValue and game.rightValue == val2) or (val2 == game.leftValue and game.rightValue == val1) 

def updateLastPlayerTime(game:DominoGame,alias:str):
    if game.player1 is not None and game.player1.alias == alias:
        game.lastTime1 = timezone.now()
    elif game.player2 is not None and game.player2.alias == alias:
        game.lastTime2 = timezone.now()
    if game.player3 is not None and game.player3.alias == alias:
        game.lastTime3 = timezone.now()
    if game.player4 is not None and game.player4.alias == alias:
        game.lastTime4 = timezone.now()
    game.save(update_fields=["lastTime1", "lastTime2", "lastTime3", "lastTime4"])

def takeRandomTile(tiles):
    list_tiles = tiles.split(',')
    
    max_double = None
    max_sum = -1
    max_tile = None
    
    for tile in list_tiles:
        num1, num2 = map(int, tile.split('|'))
        current_sum = num1 + num2
        
        # Buscar el mayor doble
        if num1 == num2:
            if current_sum > max_sum or max_double is None:
                max_double = tile
                max_sum = current_sum
                
        # Mientras tanto también buscamos la ficha con mayor suma
        if current_sum > max_sum or max_tile is None:
            max_tile = tile
            max_sum = current_sum
    
    # Devolver el mayor doble si existe, sino la mayor ficha
    return max_double if max_double is not None else max_tile

def takeRandomCorrectTile(tiles,left,right):
    list_tiles = tiles.split(',')
    best_tile = None
    best_sum = -1
    
    for tile in list_tiles:
        val1, val2 = map(int, tile.split('|'))
        current_sum = val1 + val2
        is_double = (val1 == val2)
        is_valid = (val1 == left or val1 == right or val2 == left or val2 == right)
        
        if is_valid:
            # Si es mejor que la actual (suma mayor o misma suma pero es doble)
            if (current_sum > best_sum) or (current_sum == best_sum and is_double):
                best_tile = tile if not is_double and (val1 == left or val1 == right) else rTile(tile)
                best_sum = current_sum
    
    return best_tile if best_tile is not None else "-1|-1"

def isMyTurn(myPos:int, next_player:int):
    return myPos == next_player

def getLastMoveTime(game,player):
    if game.player1 is not None and game.player1.alias == player.alias:
        return game.lastTime1
    elif game.player2 is not None and game.player2.alias == player.alias:
        return game.lastTime2
    elif game.player3 is not None and game.player3.alias == player.alias:
        return game.lastTime3
    elif game.player4 is not None and game.player4.alias == player.alias:
        return game.lastTime4
    return None

def havepoints(game: DominoGame):
    """
    Retorna si algun jugador tiene puntos en una mesa por puntos
    """
    have_points = False
    if game.perPoints:
        if game.player1 is not None and not have_points:
            have_points = game.player1.points>0
        elif game.player2 is not None and not have_points:
            have_points = game.player2.points>0
        elif game.player3 is not None and not have_points:
            have_points = game.player3.points>0
        elif game.player4 is not None and  not have_points:
            have_points = game.player4.points>0
    return have_points

def ready_to_play(game: DominoGame, player: Player)->bool:
    '''
        Comprueba si el player tiene suficientes monedas para jugar en la mesa
    '''
    
    min_amount = 0
    
    pass_number = 5
    if game.variant == 'd6':
        pass_number = 3

    if game.perPoints and game.payMatchValue>0:
        min_amount = game.payMatchValue
    elif not game.perPoints and (game.payPassValue>0 or game.payWinValue>0):
        min_amount = game.payWinValue + (game.payPassValue * pass_number)
    
    if player.total_coins >= min_amount:
        return True
    
    return False   