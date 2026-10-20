from rest_framework import status
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, When, Case, Value, FloatField
from django.db.utils import DatabaseError
from django.db import transaction
from dominoapp.models import Player, RulesGame, DominoGame, AppVersion
from dominoapp.serializers import List_Rules_Game_Serializer, GameSerializer, PlayerGameSerializer, PlayerOnListGameSerializer
from dominoapp.utils import game_tools
from dominoapp.utils.async_task_helper import safe_async_task
from dominoapp.tasks import async_update_player_presence
from dominoapp.utils.websocket_utils import send_ws_notification, send_ws_to_lobby, get_count_and_up, get_count_lobby_and_up
from dominoapp.utils.constants import WSActions
import logging
logger = logging.getLogger('django')


class RuleService:

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
        if player.lastTimeInSystem + timedelta(seconds = 10) < timezone.now():
            try:
                safe_async_task(
                    async_update_player_presence,
                    player_data = {
                        'id': player.id,
                        'inactive_player': False,
                        'send_delete_email': False,
                        'lastTimeInSystem': timezone.now().isoformat()
                    }
                )
            except Exception as e:
                logger.error(f"Error lanzando async task para actualizar presencia del jugador: {e}")

        # 3. Verificación de bloqueo más directa
        if player.is_block:
            return Response({'status': 'error', "message": "Este usuario está bloqueado, contacte con soporte."}, status=status.HTTP_409_CONFLICT)
        
        player_data = PlayerOnListGameSerializer(player).data
        
        # 4. Manejo de versión de app (evitamos try/except genérico que es lento)
        app_version = request.query_params.get('app_version')
        app_version_obj = AppVersion.objects.filter(version=app_version).first()
        need_update = app_version_obj.need_update if app_version_obj else False

        ### Para cuando cambiemos la forma de comprobar que version actualizar
        # if app_version is not None:            
        #     app_version_new = AppVersion.objects.filter(need_update=False).order_by("-id").last()
        #     if app_version_new is not None:
        #         logger.error(f"app_version: {app_version} ({type(app_version)}), app_version_new: {app_version_new.version} ({type(app_version_new.version)}), need_update: {app_version<app_version_new.version}")
                
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
            Q(player1__id=player.id) | Q(player2__id=player.id) | Q(player3__id=player.id) | Q(player4__id=player.id)
        )
        
        game_id = -1

        # Si el jugador ya está en juegos, priorizamos esos
        if active_games.exists():
            target_rules = RulesGame.objects.filter(id__in = active_games.values_list('rules__id', flat=True))
            game_id = active_games.first().id
        else:
            # Usamos el queryset original si no hay juegos activos, o el filtrado por alias           
            alias = request.query_params.get('alias')
            target_rules = queryset
            if alias:
                target_games = DominoGame.objects.filter(
                    Q(player1__alias=alias) | Q(player2__alias=alias) | 
                    Q(player3__alias=alias) | Q(player4__alias=alias)
                )
                target_rules = queryset.filter(id__in = target_games.values_list('rules__id', flat=True))

        serializer = List_Rules_Game_Serializer(target_rules, many=True)
        
        return Response({
            'status': 'success',
            "rules": serializer.data,
            "player": player_data,
            "game_id": game_id,
            "update": False
        }, status=status.HTTP_200_OK)

    @staticmethod
    def process_join(request, rule_id):
        try:
            player = Player.objects.get(user__id=request.user.id)
        except:
            return Response({"status":'error',"message":"Debe autenticarse."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            rule = RulesGame.objects.get(id=rule_id)
        except RulesGame.DoesNotExist:
            return Response({"status":'error',"message":"Mesa no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        check_others_game = DominoGame.objects.filter(
            Q(player1__id=player.id) |
            Q(player2__id=player.id) |
            Q(player3__id=player.id) |
            Q(player4__id=player.id)
        ).exists()
        if check_others_game:
            return Response({'status': 'error', "message": "Ya estas jugando en otra mesa."}, status=status.HTTP_409_CONFLICT)
                
        now = timezone.now()
        
        if player.registered_in_tournament:
            tournament = player.registered_in_tournament
            if tournament.start_at - timedelta(minutes=15) <= now and now < tournament.start_at + timedelta(minutes=5):
                return Response({'status': 'error',"message":"Estás participando en un torneo que comenzará en menos de 15 minutos."}, status=status.HTTP_409_CONFLICT)

        if player.play_tournament:
            return Response({'status': 'error',"message":"Estás participando en un torneo."}, status=status.HTTP_409_CONFLICT)

        if not game_tools.ready_to_play_rule(rule, player):
            return Response({"status":'error',"message":"Monedas insuficientes."},status=status.HTTP_409_CONFLICT)
                
        games = DominoGame.objects.filter(rules__id = rule.id).exclude(player4__isnull = False).annotate(
            total_players = Case(
                    When(
                        player4__isnull=False, 
                        then=Value(4.0)
                    ),
                    When(
                        player3__isnull=False, 
                        then=Value(3.0)
                    ),
                    When(
                        player2__isnull=False, 
                        then=Value(2.0)
                    ),
                    When(
                        player1__isnull=False, 
                        then=Value(1.0)
                    ),
                    default=Value(0),
                    output_field=FloatField()
                )
        )
        orded_games = games.order_by("-total_players")
                  
        try:            
            with transaction.atomic():  
                if orded_games.exists():
                    select_game = orded_games.first()
                else:
                    select_game = DominoGame.objects.create(
                        rules = rule,
                        variant = rule.variant,
                        maxScore = rule.maxScore,
                        inPairs = rule.inPairs,
                        perPoints = rule.perPoints,
                        startWinner = rule.startWinner,
                        lostStartInTie = rule.lostStartInTie,
                        payPassValue = rule.payPassValue,
                        payMatchValue = rule.payMatchValue,
                        max_coins = rule.max_coins,
                        max_datas = rule.max_datas,
                        sumAllPoints = rule.sumAllPoints,
                        capicua = rule.capicua,
                        moveTime = rule.moveTime,
                        password = rule.password                        
                    )              

                try:
                    game = DominoGame.objects.select_related(
                        'player1', 'player2', 'player3', 'player4'
                    ).select_for_update(of=('self',), nowait=True).get(id=select_game.id)
                except DominoGame.DoesNotExist:
                    return Response({"status":'error',"message":"Mesa no encontrada."}, status=status.HTTP_404_NOT_FOUND)

                is_in_game,players_in_game = game_tools.checkPlayerJoined(player,game)
                
                slot_assigned = False
                if not is_in_game:
                    # Buscar el primer slot libre                    
                    for i in range(4):
                        attr = f'player{i+1}'
                        if getattr(game, attr) is None:
                            setattr(game, attr, player)
                            players_in_game.append(player)
                            slot_assigned = True
                            break
                
                    if not slot_assigned:
                        return Response({'status': 'error', "message": "Mesa llena."}, status=status.HTTP_409_CONFLICT)

                # 4. Actualización de Estado de la Mesa
                if slot_assigned:
                    num_players = len(players_in_game)
                    if game.inPairs:
                        game.status = "ready" if num_players == 4 and game.status == "wt" else "wt"
                    else:
                        if num_players >= 2 and game.status not in ["ru", "fi", "fg"]:
                            game.status = "ready"
                        elif num_players < 2:
                            game.status = "wt"
                    
                    game.save(update_fields=["status", "player1", "player2", "player3", "player4"])
                    
                    try:
                        count_key = get_count_and_up(game.id)
                        transaction.on_commit(lambda ck=count_key: send_ws_notification(
                            game_id= game.id,
                            payload={
                                "a": WSActions.PLAYER_JOINED,
                                "cg": ck,
                                "d": {
                                    "st": game.status,
                                    "p": player.id,
                                    "pn": player.name,
                                    "pa": player.alias,
                                    "pc": player.total_coins,
                                    "pp": player.photo_url,
                                    "pi": player.isPlaying
                                }
                            }
                        ))
                    except Exception as error:
                        logger.error(f"Error al enviar el WS en el join. Error: {error}")

                    try:
                        count_key = get_count_lobby_and_up()
                        transaction.on_commit(lambda ck=count_key: send_ws_to_lobby(
                            payload={
                                "a": WSActions.GAME_UPDATE,
                                "cg": ck,
                                "d": {
                                    "gid": game.id,
                                    "st": game.status,
                                    "number_player": game.count_players
                                } 
                            }
                        ))
                    except Exception as error:
                        logger.error(f"Error enviando el ws del lobby en el join. Error: {error}")

                player.inactive_player = False
                player.send_delete_email = False
                player.lastTimeInSystem = now
                player.lastTimeInGame = now
                if game.status in ["wt", "ready"]:
                    player.tiles = "" # Limpiar fichas si el juego no ha empezado
                
                player.save(update_fields=["inactive_player", "send_delete_email", "lastTimeInSystem", "lastTimeInGame", "tiles"])                
                
                serializerGame = GameSerializer(game)
                playerSerializer = PlayerGameSerializer(players_in_game,many=True)
                return Response({'status': 'success', "game":serializerGame.data,"players":playerSerializer.data}, status=200)
                
        except DatabaseError as error:
            # Si alguien más tiene el candado y usamos nowait=True (opcional) 
            # o hay un error de colisión de DB.
            return Response({'status': 'error', "message": "La mesa está ocupada en este momento."}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            print("error: ", str(e))
            return Response({'status': 'error', "message": "Algo salio mal, vuelva a intentar."}, status=status.HTTP_409_CONFLICT)




