from rest_framework import status, serializers
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
from dominoapp.models import Player, DominoGame, AppVersion, BlockPlayer, Round
from dominoapp.serializers import ListGameSerializer, GameSerializer, PlayerLoginSerializer, PlayerGameSerializer
from dominoapp.utils import game_tools
from dominoapp.connectors.pusher_connector import PushNotificationConnector


class GameService:

    @staticmethod
    def process_list(request, queryset):
        user = request.user
        is_block = BlockPlayer.objects.filter(player_blocked__user__id=user.id).exists()
        if is_block:
            return Response({'status': 'error', "message":"These user is block, contact suport"}, status=status.HTTP_409_CONFLICT)

        check = Player.objects.filter(user__id = user.id ).exists()
        if not check:
            return Response ({'status': 'error', "message": "Player not found"},status=status.HTTP_404_NOT_FOUND)
        
        player = Player.objects.get(user__id=user.id)
        player.lastTimeInSystem = timezone.now()
        player.inactive_player = False
        player.send_delete_email = False
        player.save()
        playerSerializer = PlayerLoginSerializer(player)
        
        game_id = -1
        
        app_version = request.query_params.get('app_version', None)
        try:
            app_version_obj = AppVersion.objects.get(version = app_version)
        except:
            app_version_obj = None
        
        if app_version_obj and app_version_obj.need_update:
            return Response({'status': 'success', "games":[],"player":playerSerializer.data,"game_id":game_id,"update":app_version_obj.need_update}, status=200)
                
        inGame = DominoGame.objects.filter(
            Q(player1__id = player.id)|
            Q(player2__id = player.id)|
            Q(player3__id = player.id)|
            Q(player4__id = player.id)
            ).exists()
        if inGame:
            games = DominoGame.objects.filter(
            Q(player1__id = player.id)|
            Q(player2__id = player.id)|
            Q(player3__id = player.id)|
            Q(player4__id = player.id)
            )
            game_id = games.first().id
            serializer =ListGameSerializer(games,many=True)
            return Response({
                        'status': 'success', 
                        "games":serializer.data,
                        "player":playerSerializer.data,
                        "game_id":game_id,
                        "update": False
                            }, status=status.HTTP_200_OK)
        alias = request.query_params.get('alias', None)
        
        if alias is not None:
            queryset = queryset.filter(
                Q(player1__alias = alias)|
                Q(player2__alias = alias)|
                Q(player3__alias = alias)|
                Q(player4__alias = alias)
                )

        serializer =ListGameSerializer(queryset,many=True)
        return Response({
                    'status': 'success', 
                    "games":serializer.data,
                    "player":playerSerializer.data,
                    "game_id":game_id,
                    "update": False
                         }, status=status.HTTP_200_OK)
    
    @staticmethod
    def process_retrieve(request, game_id):

        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        game = DominoGame.objects.get(id = game_id)
        serializer = GameSerializer(game)
        
        players = []
        if game.player1 is not None:
            players.insert(0,game.player1)
        if game.player2 is not None:
            players.insert(1, game.player2)
        if game.player3 is not None:
            players.insert(2, game.player3)
        if game.player4 is not None:
            players.insert(3, game.player4)
        
        players_data = PlayerGameSerializer(players, many=True).data

        return Response({'status': 'success', "game":serializer.data,"players":players_data}, status=status.HTTP_200_OK)
    
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

        player1.tiles = ""
        player1.lastTimeInSystem = timezone.now()
        player1.inactive_player = False
        player1.save()

        data = request.data.copy()
        data["lastTime1"] = timezone.now()
        data["player1"] = player1.id
        
        game_serializer = GameSerializer(data = data)
        try:
            game_serializer.is_valid(raise_exception=True)
            game: DominoGame =  game_serializer.save()
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
        
        player = Player.objects.get(user__id=request.user.id)
                
        player.lastTimeInSystem = timezone.now()
        player.inactive_player = False
        player.send_delete_email = False
        player.save()

        check_others_game = DominoGame.objects.filter(
            Q(player1__id = player.id)|
            Q(player2__id = player.id)|
            Q(player3__id = player.id)|
            Q(player4__id = player.id)
        ).exclude(id = game_id).exists()

        if check_others_game:
            return Response({'status': 'error',"message":"the player is play other game"}, status=status.HTTP_409_CONFLICT)

        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        game = DominoGame.objects.get(id=game_id)
        
        game_in_round = Round.objects.filter(game_list__id = game.id).exists()
        
        if player.play_tournament and not game_in_round:
            return Response({'status': 'error',"message":"Estas jugando en un torneo."}, status=status.HTTP_409_CONFLICT)
                
        if not game_tools.ready_to_play(game, player):
            return Response({"status":'error',"message":"you don't have enough coins"},status=status.HTTP_409_CONFLICT)
        
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
                if len(players) == 4 and game.status != "ru":
                    game.status = "ready"
                elif game.status != "ru":
                    game.status = "wt"
            else:                
                if len(players) >= 2 and game.status != "ru" and game.status != "fi":
                    game.status = "ready"
                elif game.status != "ru" and game.status != "fi":
                    game.status = "wt"
            if game.status == "wt" or game.status == "ready":
                for player in players:
                    player.tiles=""
                    player.save()            
            # game_tools.updateLastPlayerTime(game,alias)
            game.save()    
            serializerGame = GameSerializer(game)
            PushNotificationConnector.push_notification(
                channel=f'mesa_{game.id}',
                event_name='join_player',
                data_notification={
                    'game_status': game.status,
                    'player': player.id,
                    'time': timezone.now().strftime("%d/%m/%Y, %H:%M:%S")
                }
            )
            playerSerializer = PlayerGameSerializer(players,many=True)
            return Response({'status': 'success', "game":serializerGame.data,"players":playerSerializer.data}, status=200)
        else:
            return Response({'status': 'error', "message":"Full players"}, status=status.HTTP_409_CONFLICT)
        
    @staticmethod
    def process_start(game_id):

        check_game = DominoGame.objects.filter(id = game_id).exclude(tournament__isnull = False).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        game = DominoGame.objects.get(id=game_id)
        if game.status != "wt":
            players = game_tools.playersCount(game)
            for player in players:
                if not game_tools.ready_to_play(game, player):
                        game_tools.exitPlayer(game,player,players,len(players))            
            
            ### Actualizo los players por si se saco alguno
            players = game_tools.playersCount(game)
            if (game.inPairs and len(players)<4) or len(players)<2:
                return Response({"status":'error',"message":"not enough players"},status=status.HTTP_409_CONFLICT)
            game_tools.startGame1(game.id,players)    
            serializerGame = GameSerializer(game)
            playerSerializer = PlayerGameSerializer(players,many=True)
            PushNotificationConnector.push_notification(
                channel=f'mesa_{game.id}',
                event_name='start_game',
                data_notification={
                    'game_status': game.status,
                    'starter': game.starter,
                    'next_player': game.next_player,
                    'time': timezone.now().strftime("%d/%m/%Y, %H:%M:%S")
                }
            )
            return Response({'status': 'success', "game":serializerGame.data,"players":playerSerializer.data}, status=200)
        return Response ({'status': 'error', "message": "game is running"},status=status.HTTP_409_CONFLICT)
    
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
            
            error = game_tools.move1(game_id,player.alias,tile)
            if error is None:
                profile = Player.objects.get(alias = player.alias)
                profile.lastTimeInSystem = timezone.now()
                profile.inactive_player = False
                profile.save()
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
            PushNotificationConnector.push_notification(
                channel=f'mesa_{game.id}',
                event_name='exit_player',
                data_notification={
                    'game_status': game.status,
                    'player': player.id,
                    'time': timezone.now().strftime("%d/%m/%Y, %H:%M:%S")
                }
            )
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
            game_tools.setWinnerStarterNext1(game,request.data["winner"],request.data["starter"],request.data["next_player"])
            game.save()
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