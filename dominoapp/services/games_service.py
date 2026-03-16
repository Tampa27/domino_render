from rest_framework import status, serializers
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.db.utils import DatabaseError
from django.db import transaction
from dominoapp.models import Player, DominoGame, AppVersion, BlockPlayer, Round
from dominoapp.serializers import ListGameSerializer, GameSerializer, PlayerLoginSerializer, PlayerGameSerializer
from dominoapp.utils import game_tools
from dominoapp.connectors.pusher_connector import PushNotificationConnector
import logging
logger = logging.getLogger('django')


class GameService:

    @staticmethod
    def process_list(request, queryset):
    
        # 1. Usar select_related para traer al User de una vez si el Serializer lo necesita
        # NO usar select_for_update aquí.
        player = Player.objects.filter(user_id=request.user.id).first()
        
        if not player:
            return Response({'status': 'error', "message": "Jugador no encontrado."}, status=404)

        # 2. ACTUALIZACIÓN ASÍNCRONA O ATÓMICA SIN BLOQUEO
        # Solo actualizamos si ha pasado un tiempo prudencial (ej. 1 minuto) 
        # o usamos .update() directamente para evitar el overhead de .save()
        Player.objects.filter(id=player.id).update(
            lastTimeInSystem=timezone.now(),
            inactive_player=False,
            send_delete_email=False
        )
        
        # 3. Verificación de bloqueo más directa
        if BlockPlayer.objects.filter(player_blocked=player).exists():
            return Response({'status': 'error', "message": "Este usuario está bloqueado, contacte con soporte."}, status=status.HTTP_409_CONFLICT)
        
        player_data = PlayerLoginSerializer(player).data
        
        # 4. Manejo de versión de app (evitamos try/except genérico que es lento)
        app_version = request.query_params.get('app_version')
        app_version_obj = AppVersion.objects.filter(version=app_version).first()
        
        need_update = app_version_obj.need_update if app_version_obj else False
        
        if need_update:
            return Response({
                'status': 'success', 
                "games": [], 
                "player": player_data, 
                "game_id": -1, 
                "update": True
            }, status=status.HTTP_200_OK)

        # 5. Optimización de consulta de juegos
        # Filtramos los juegos activos del jugador
        active_games = DominoGame.objects.filter(
            Q(player1=player) | Q(player2=player) | Q(player3=player) | Q(player4=player)
        )
        
        # Usamos el queryset original si no hay juegos activos, o el filtrado por alias
        game_id = -1
        alias = request.query_params.get('alias')
        
        # Si el jugador ya está en juegos, priorizamos esos
        if active_games.exists():
            target_games = active_games
            game_id = target_games.first().id
        else:
            # Si no está en juegos, usamos el queryset base (posiblemente juegos disponibles)
            target_games = queryset
            if alias:
                target_games = target_games.filter(
                    Q(player1__alias=alias) | Q(player2__alias=alias) | 
                    Q(player3__alias=alias) | Q(player4__alias=alias)
                )

        serializer = ListGameSerializer(target_games, many=True)
        
        return Response({
            'status': 'success', 
            "games": serializer.data,
            "player": player_data,
            "game_id": game_id,
            "update": False
        }, status=status.HTTP_200_OK)
    
    @staticmethod
    def process_retrieve(request, game_id):
        # 1. Traemos el juego y sus jugadores en una SOLA consulta usando select_related
        # Esto evita que al acceder a game.player1 se haga otra consulta a la DB.
        try:
            game = DominoGame.objects.select_related(
                'player1', 'player2', 'player3', 'player4'
            ).get(id=game_id)
        except DominoGame.DoesNotExist:
            return Response(
            
                {"status": "error", "message": "game not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Actualizar el timestamp del jugador de forma eficiente
        # Solo si el usuario está autenticado
        if request.user.is_authenticated:
            try:
                # Usamos select_for_update con nowait=True en un bloque atómico pequeño
                # para intentar "marcar" al jugador. Si está bloqueado, saltamos al except.
                with transaction.atomic():
                    Player.objects.filter(
                        user_id=request.user.id
                    ).select_for_update(nowait=True).update(lastTimeInSystem=timezone.now())
            except DatabaseError:
                # Si el jugador está bloqueado (moviendo ficha), ignoramos la actualización
                # del timestamp para esta petición de "retrieve". 
                # No pasa nada, porque la transacción del movimiento actualizará el tiempo después.
                pass

        # 3. Serializar el juego
        serializer = GameSerializer(game)

        # 4. Construir la lista de jugadores filtrando los None de forma elegante
        players = [p for p in [game.player1, game.player2, game.player3, game.player4] if p is not None]
        players_data = PlayerGameSerializer(players, many=True).data

        return Response({
            'status': 'success', 
            "game": serializer.data, 
            "players": players_data
        }, status=status.HTTP_200_OK)
    
    @staticmethod
    def process_create(request):
        
        player1 = Player.objects.get(user__id= request.user.id)
        check_others_game = DominoGame.objects.filter(
            Q(player1__id = player1.id)|
            Q(player2__id = player1.id)|
            Q(player3__id = player1.id)|
            Q(player4__id = player1.id)
        ).exists()

        if check_others_game:
            return Response({'status': 'error',"message":"the player is play other game"}, status=status.HTTP_409_CONFLICT)

        if player1.registered_in_tournament and player1.registered_in_tournament.start_at - timedelta(minutes=30) <= timezone.now():
            return Response({'status': 'error',"message":"El torneo comenzará en menos de 30 minutos."}, status=status.HTTP_409_CONFLICT)

        if player1.play_tournament:
            return Response({'status': 'error',"message":"Estas jugando en un torneo."}, status=status.HTTP_409_CONFLICT)
        
        player1.tiles = ""
        player1.lastTimeInSystem = timezone.now()
        player1.lastTimeInGame = timezone.now()
        player1.inactive_player = False
        player1.save(update_fields=["tiles", "lastTimeInSystem", "lastTimeInGame", "inactive_player"])

        data = request.data.copy()
        data["lastTime1"] = timezone.now()
        data["player1"] = player1.id
        
        game_serializer = GameSerializer(data = data)
        try:
            game_serializer.is_valid(raise_exception=True)
            game: DominoGame =  game_serializer.save()
            if not game_tools.ready_to_play(game,player1):
                players = game_tools.playersCount(game)
                game_tools.exitPlayer(game,player1,players,len(players))
                return Response({"status": "error", "message": "No tienes suficientes monedas para crear esta mesa"}, status=status.HTTP_409_CONFLICT)
                        
        except serializers.ValidationError as e:
            return Response(
                {'status': 'error', 'message': 'Invalid data', 'errors': e.detail},
                status=400
            )
        except Exception as error:
            return Response({'status': 'error', "message":"Something is wrong at save game"}, status=409)

        game_tools.updateLastPlayerTime(game,player1.alias)
                
        return Response({'status': 'success', "game":game_serializer.data}, status=200)
    
    @staticmethod
    def process_join(request, game_id):
        try:
            with transaction.atomic():
                # 1. Bloqueamos al jugador que intenta unirse (el "peticionario")
                player = Player.objects.select_for_update().get(user__id=request.user.id)
                
                # Actualizamos sus datos de presencia
                player.lastTimeInSystem = timezone.now()
                player.lastTimeInGame = timezone.now()
                player.inactive_player = False
                player.send_delete_email = False
                player.save(update_fields=["lastTimeInSystem", "lastTimeInGame", "inactive_player", "send_delete_email"])

                # 2. Bloqueamos la mesa Y a los jugadores que ya están en ella (player1...player4)
                # Usamos select_related para traerlos en una sola consulta y bloquearlos con 'of'
                try:
                    game = DominoGame.objects.select_for_update().get(id=game_id)
                except DominoGame.DoesNotExist:
                    return Response({"status":'error',"message":"Mesa no encontrada."}, status=status.HTTP_404_NOT_FOUND)

                # 3. Bloqueamos a los jugadores que YA están sentados de forma independiente
                # Esto evita el error de PostgreSQL
                player_ids = [pid for pid in [game.player1_id, game.player2_id, game.player3_id, game.player4_id] if pid]
                if player_ids:
                    # Al hacer list() forzamos la ejecución del select_for_update en la DB
                    list(Player.objects.select_for_update().filter(id__in=player_ids))
                
                # 3. Validaciones de negocio (Ahora son seguras porque nadie puede cambiar al player ni a la mesa)
                check_others_game = DominoGame.objects.filter(
                    Q(player1__id=player.id) |
                    Q(player2__id=player.id) |
                    Q(player3__id=player.id) |
                    Q(player4__id=player.id)
                ).exclude(id=game_id).exists()
                if check_others_game:
                    return Response({'status': 'error', "message": "Ya estas jugando en otra mesa."}, status=status.HTTP_409_CONFLICT)
        
                game_in_round = Round.objects.filter(game_list__id = game.id).exists()
                if not game_in_round and player.registered_in_tournament and player.registered_in_tournament.start_at - timedelta(minutes=30) <= timezone.now() and timezone.now() < player.registered_in_tournament.start_at + timedelta(minutes=5):
                    return Response({'status': 'error',"message":"El torneo comenzará en menos de 30 minutos."}, status=status.HTTP_409_CONFLICT)

                if player.play_tournament and not game_in_round:
                    return Response({'status': 'error',"message":"Estas jugando en un torneo."}, status=status.HTTP_409_CONFLICT)
                        
                if not game_tools.ready_to_play(game, player):
                    return Response({"status":'error',"message":"No tienes suficientes monedas para jugar en esta mesa."},status=status.HTTP_409_CONFLICT)
        
                joined,players = game_tools.checkPlayerJoined(player,game)
                if joined != True:
                    if game.player1 is None:
                        game.player1 = player
                        joined = True
                        players.insert(0,player)
                    elif game.player2 is None:
                        game.player2 = player
                        joined = True
                        players.insert(1,player)
                    elif game.player3 is None :
                        game.player3 = player
                        joined = True
                        players.insert(2,player)
                    elif game.player4 is None:
                        game.player4 = player
                        joined = True
                        players.insert(3,player)

                if joined == True:
                    if game.inPairs:
                        if len(players) == 4 and game.status == "wt":
                            game.status = "ready"
                        elif len(players) != 4:
                            game.status = "wt"
                    else:                
                        if len(players) >= 2 and game.status not in ["ru", "fi"]:
                            game.status = "ready"
                        elif game.status not in ["ru", "fi"]:
                            game.status = "wt"
                    # 5. Limpieza de fichas (Seguro porque todos en current_players están bloqueados)
                    if game.status in ["wt", "ready"]:
                        for p in players:
                            if p.tiles != "": # Optimización: solo guardar si es necesario
                                p.tiles = ""
                                p.save(update_fields=["tiles"])          
                    # game_tools.updateLastPlayerTime(game,alias)
                    game.save(update_fields=["status", "player1", "player2", "player3", "player4"])    
                    serializerGame = GameSerializer(game)
                    ## No se estan usando y estan demorando los request       
                    # PushNotificationConnector.push_notification(
                    #     channel=f'mesa_{game.id}',
                    #     event_name='join_player',
                    #     data_notification={
                    #         'game_status': game.status,
                    #         'player': player.id,
                    #         'time': timezone.now().strftime("%d/%m/%Y, %H:%M:%S")
                    #     }
                    # )
                    playerSerializer = PlayerGameSerializer(players,many=True)
                    return Response({'status': 'success', "game":serializerGame.data,"players":playerSerializer.data}, status=200)
                else:
                    return Response({'status': 'error', "message":"Mesa llena"}, status=status.HTTP_409_CONFLICT)
        except DatabaseError as error:
            # Si alguien más tiene el candado y usamos nowait=True (opcional) 
            # o hay un error de colisión de DB.
            logger.error(f"La mesa {game_id} está ocupada en este momento. Error: {error}")
            return Response({'status': 'error', "message": "La mesa está ocupada en este momento."}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"Erro al intentar unirse a la mesa {game_id}, Error: {e}")
            return Response({'status': 'error', "message": "Algo salio mal, vuelva a intentar."}, status=500)
        
    @staticmethod
    def process_start(game_id):
        # 1. Validación rápida fuera de la transacción (opcional, para liberar carga)
        check_game = DominoGame.objects.filter(id=game_id).exclude(tournament__isnull=False).exists()
        if not check_game:
            return Response({"status": 'error', "message": "Mesa no disponible."}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                # 2. Bloqueamos la mesa y a los 4 jugadores relacionados
                # Usamos select_related para traerlos de una vez y 'of' para fijar sus filas
                try:
                    game = DominoGame.objects.select_for_update().get(id=game_id)
                except DominoGame.DoesNotExist:
                    return Response({"status":'error',"message":"Mesa no encontrada."}, status=status.HTTP_404_NOT_FOUND)

                # 3. Bloqueamos a los jugadores que YA están sentados de forma independiente
                # Esto evita el error de PostgreSQL
                player_ids = [pid for pid in [game.player1_id, game.player2_id, game.player3_id, game.player4_id] if pid]
                if player_ids:
                    # Al hacer list() forzamos la ejecución del select_for_update en la DB
                    list(Player.objects.select_for_update().filter(id__in=player_ids))
                
                # IMPORTANTE: Según tu lógica, el juego solo arranca si NO está en "wt" (waiting)
                if game.status != "wt":
                    # 3. Obtenemos los jugadores bloqueados directamente desde la instancia 'game'
                    players = game_tools.playersCount(game)
                    
                    # 4. Verificación de "Ready to Play" y limpieza
                    # Como los jugadores están bloqueados, nadie puede "gastar sus monedas" 
                    # en otra mesa mientras hacemos este bucle.
                    for player in players:
                        if not game_tools.ready_to_play(game, player):
                            # Esta función debe actualizar game.playerX = None
                            game_tools.exitPlayer(game, player, players, len(players))
                    
                    # 5. Re-validamos la cantidad de jugadores después de las posibles salidas
                    players = game_tools.playersCount(game)
                    
                    if (game.inPairs and len(players) < 4) or len(players) < 2:
                        return Response({"status": 'error', "message": "No hay players suficientes para jugar esta partida."}, status=status.HTTP_409_CONFLICT)
                    
                    # 6. Comenzar el juego (repartir fichas, cambiar status a 'ru')
                    # startGame1 ahora es seguro porque tiene el candado de los 4 players y la mesa
                    game_tools.startGame1(game, players)
                    
                    # Serialización
                    serializerGame = GameSerializer(game)
                    playerSerializer = PlayerGameSerializer(players, many=True)

                    ## No se estan usando y estan demorando los request       
                    # PushNotificationConnector.push_notification(
                    #     channel=f'mesa_{game.id}',
                    #     event_name='start_game',
                    #     data_notification={
                    #         'game_status': game.status,
                    #         'starter': game.starter,
                    #         'next_player': game.next_player,
                    #         'time': timezone.now().strftime("%d/%m/%Y, %H:%M:%S")
                    #     }
                    # )
                    return Response({'status': 'success', "game":serializerGame.data,"players":playerSerializer.data}, status=200)
            # Si el status es "wt", significa que aún no cumple requisitos para iniciar
            return Response ({'status': 'error', "message": "Ya el juego ha comenzado."},status=status.HTTP_409_CONFLICT)
        except DatabaseError as error:
            # Si alguien más está intentando iniciar el juego o uniéndose justo ahora
            logger.error(f"La mesa {game_id} está ocupada en este momento. Error: {error}")
            return Response({'status': 'error', "message": "La mesa está ocupada procesando otra acción."}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            return Response ({'status': 'error', "message": "Algo anda mal, vuelva a intentar."},status=status.HTTP_409_CONFLICT)
    
    @staticmethod
    def process_move(request, game_id):
        tile = request.data["tile"]
        try:
            check = DominoGame.objects.filter(id=game_id).exists()
            if not check:
                return Response({'status': 'error', 'message': "Game not found"}, status=404)
            check = Player.objects.filter(user__id=request.user.id).exists()
            if not check:
                return Response({'status': 'error', 'message': "Player not found"}, status=404)
            
            player = Player.objects.get(user__id=request.user.id)
            filteres = Q(player1__alias=player.alias)|Q(player2__alias=player.alias)|Q(player3__alias=player.alias)|Q(player4__alias=player.alias)
            check = DominoGame.objects.filter(filteres).filter(id=game_id).exists()
            if not check:
                return Response({'status': 'error', 'message': "These Player are not in this game"}, status=400)
            
            error = game_tools.move1(game_id,player.id,tile)
            if error is None:
                profile = Player.objects.get(alias = player.alias)
                profile.lastTimeInSystem = timezone.now()
                profile.lastTimeInGame = timezone.now()
                profile.inactive_player = False
                profile.save(update_fields=["lastTimeInSystem","lastTimeInGame","inactive_player"])
                return Response({'status': 'success'}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'error', 'message': error}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:        
            return Response({'status':'error', "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @staticmethod
    def process_exitGame(request, game_id):

        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        game = DominoGame.objects.get(id=game_id)
        player = Player.objects.get(user__id=request.user.id)

        game_in_round = Round.objects.filter(game_list__id = game.id).exists()
        if game_in_round:
            return Response({'status': 'error', "message":"No puedes salir de un juego de un torneo."}, status=status.HTTP_409_CONFLICT)
        
        if game.status in ["ru","fi"] and player.isPlaying and game.perPoints:
            have_points = game_tools.havepoints(game)
            if have_points:
                return Response({'status': 'error', "message":"The game is not over, wait until it's over."}, status=status.HTTP_409_CONFLICT)
        elif game.status in ["ru"] and player.isPlaying:
                return Response({'status': 'error', "message":"The game is not over, wait until it's over."}, status=status.HTTP_409_CONFLICT)
        
        players = game_tools.playersCount(game)
        exited = game_tools.exitPlayer(game,player,players,len(players))
        if exited:
            ## No se estan usando y estan demorando los request       
            # PushNotificationConnector.push_notification(
            #     channel=f'mesa_{game.id}',
            #     event_name='exit_player',
            #     data_notification={
            #         'game_status': game.status,
            #         'player': player.id,
            #         'time': timezone.now().strftime("%d/%m/%Y, %H:%M:%S")
            #     }
            # )
            return Response({'status': 'success'}, status=200)
        return Response({'status': 'error', "message":'Player no found'}, status=404)
    
    @staticmethod
    def process_setwinner(request, game_id):

        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        with transaction.atomic():
            game = DominoGame.objects.select_for_update().get(id=game_id)

            game_tools.setWinner1(game,request.data["winner"])
            game.save()
        return Response({'status': 'success'}, status=200)
    
    @staticmethod
    def process_setstarter(request, game_id):
        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        with transaction.atomic():
            game = DominoGame.objects.select_for_update().get(id=game_id)
            game.starter = request.data["starter"]
            game.save()
        
        return Response({'status': 'success'}, status=200)

    @staticmethod
    def process_setWinnerStarter(request, game_id):
        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        with transaction.atomic():
            game = DominoGame.objects.select_for_update().get(id=game_id)
            game.starter = request.data["starter"]
            game.winner = request.data["winner"]
            game.save()
        return Response({'status': 'success'}, status=200)
    
    @staticmethod
    def process_setWinnerStarterNext(request, game_id):
        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        with transaction.atomic():
            game = DominoGame.objects.select_for_update().get(id=game_id)
            select_starter = (game.inPairs and game.startWinner)
            if not select_starter:
                return Response(data ={
                    "status":'error',
                    "message": "En este juego no se permite seleccionar al salidor."
                }, status = status.HTTP_401_UNAUTHORIZED)
            if game.winner < DominoGame.Tie_Game:
                return Response(data ={
                    "status":'error',
                    "message": "Ya se ha seleccionado un salidor."
                }, status = status.HTTP_401_UNAUTHORIZED)
            
            game_tools.setWinnerStarterNext1(game,request.data["winner"],request.data["starter"],request.data["next_player"])
            game.save(update_fields= ["starter", "winner", "next_player", "start_time"])
        return Response({'status': 'success'}, status=200)

    @staticmethod
    def process_setPatner(request, game_id):

        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        with transaction.atomic():
            game = DominoGame.objects.select_for_update().get(id=game_id)
            
            game_in_round = Round.objects.filter(game_list__id = game.id).exists()
            if game_in_round:
                return Response({'status': 'error', "message":"No se pueden cambiar las parejas en un torneo."}, status=status.HTTP_409_CONFLICT)
            
            if game.player1.alias != request.data["alias"] and game.player2.alias != request.data["alias"] and game.player3.alias != request.data["alias"] and game.player4.alias != request.data["alias"]:
                return Response({"status":'error',"message":"The Player are not play in this game"},status=status.HTTP_409_CONFLICT)    
            
            players = game_tools.playersCount(game)
            # if game.inPairs and (game.payMatchValue > 0 or game.payWinValue > 0):
            #     return Response({'status': 'success'}, status=200)  
            # else:    
            for player in players:
                if player.alias == request.data["alias"]:
                    patner = player
                    break
            aux = game.player3
            if game.player2.alias == request.data["alias"]:
                game.player2 = aux
                game.player3 = patner
            elif game.player4.alias == request.data["alias"]:
                game.player4 = aux
                game.player3 = patner
            game.save()    
        return Response({'status': 'success'}, status=200) 