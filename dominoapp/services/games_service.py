from rest_framework import status, serializers
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from dominoapp.models import Player, DominoGame,MatchGame, DataGame, AppVersion, BlockPlayer
from dominoapp.serializers import ListGameSerializer, GameSerializer, GameRetrieveSerializer,PlayerLoginSerializer, PlayerGameSerializer
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
                
        inGame = DataGame.objects.filter(
            Q(player1__id = player.id)|
            Q(player2__id = player.id)|
            Q(player3__id = player.id)|
            Q(player4__id = player.id)
            ).filter(active=True)
        if inGame.exists():
            game=inGame.first().match.domino_game
            games = DominoGame.objects.filter(id = game.id)
            serializer =ListGameSerializer(games,many=True)
            return Response({
                        'status': 'success', 
                        "games":serializer.data,
                        "player":playerSerializer.data,
                        "game_id":game.id,
                        "update": False
                            }, status=status.HTTP_200_OK)
        alias = request.query_params.get('alias', None)
        
        if alias is not None:
            game_ids = DataGame.objects.filter(Q(player1__alias = alias)|
                Q(player2__alias = alias)|
                Q(player3__alias = alias)|
                Q(player4__alias = alias)).filter(active=True).values_list('match__domino_game__id')
            queryset = queryset.filter(
                id__in = game_ids
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
        serializer = GameRetrieveSerializer(game)
        
        data = DataGame.objects.filter(active=True, match__domino_game__id = game.id).order_by('-id').first()

        players = game_tools.playersCount(data)
        
        players_data = PlayerGameSerializer(players, many=True).data

        return Response({'status': 'success', "game":serializer.data,"players":players_data}, status=status.HTTP_200_OK)
    
    @staticmethod
    def process_create(request):
        
        player1 = Player.objects.get(user__id= request.user.id)
        check_others_game = DataGame.objects.filter(active=True).filter(
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
        game_serializer = GameSerializer(data = data)
        try:
            game_serializer.is_valid(raise_exception=True)
            game: DominoGame =  game_serializer.save()
            
            match = MatchGame.objects.create(
                domino_game = game,
                active=True,
                status='wt'
            )
            
            DataGame.objects.create(
                match = match,
                active=True,
                status='wt',
                player1= player1
            )
            
        except serializers.ValidationError as e:
            return Response(
                {'status': 'error', 'message': 'Invalid data', 'errors': e.detail},
                status=400
            )
        except Exception as error:
            return Response({'status': 'error', "message":f"Something is wrong at save game. Error->: {error}"}, status=409)
        
        game_serializer = GameRetrieveSerializer(game)
        PushNotificationConnector.push_notification(
            channel=f'mesa_{game.id}',
            event_name='create_game',
            data_notification={
                'game_status': 'wt',
                'player': player1.id,
                'time': timezone.now().strftime("%d/%m/%Y, %H:%M:%S")
            }
        )
        return Response({'status': 'success', "game":game_serializer.data}, status=200)
    
    @staticmethod
    def process_join(request, game_id):
        
        player = Player.objects.get(user__id=request.user.id)
                
        player.lastTimeInSystem = timezone.now()
        player.inactive_player = False
        player.save()

        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        game = DominoGame.objects.get(id=game_id)
                
        check_others_game = DataGame.objects.filter(active=True).filter(
            Q(player1__id = player.id)|
            Q(player2__id = player.id)|
            Q(player3__id = player.id)|
            Q(player4__id = player.id)
        ).exists()

        if check_others_game:
            return Response({'status': 'error',"message":"the player is play other game"}, status=status.HTTP_409_CONFLICT)
          
        if not game_tools.ready_to_play(game, player):
            return Response({"status":'error',"message":"you don't have enough coins"},status=status.HTTP_409_CONFLICT)
        
        data_game = DataGame.objects.filter(match__domino_game__id = game.id, active=True).order_by('-id').first()
        
        joined,players = game_tools.checkPlayerJoined(player,data_game)
        if joined != True:
            joined, players = game_tools.joinplayer(data_game, player, players)

        if joined == True:
            if game.inPairs:
                if len(players) == 4 and game.status != "ru":
                    data_game.status = "ready"
                    data_game.match.status = "ready"
                elif game.status != "ru":
                    data_game.status = "wt"
                    data_game.match.status = "wt"
            else:                
                if len(players) >= 2 and game.status != "ru" and game.status != "fi":
                    data_game.status = "ready"
                    data_game.match.status = "ready"
                elif game.status != "ru" and game.status != "fi":
                    data_game.status = "wt"
                    data_game.match.status = "wt"
            if game.status == "wt" or game.status == "ready":
                for player in players:
                    player.tiles=""
                    player.save()            
            
            data_game.match.save()
            data_game.save()
            
            serializerGame = GameRetrieveSerializer(game)
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

        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        game = DominoGame.objects.get(id=game_id)
        
        if game.status != "wt":
            data = DataGame.objects.filter(active=True, match__domino_game__id = game.id).order_by('-id').first()
            players = game_tools.playersCount(data)
            for player in players:
                if not game_tools.ready_to_play(game, player):
                        game_tools.exitPlayer(data,player,players,len(players))            
            
            ### Actualizo los players por si se saco alguno
            players = game_tools.playersCount(data)
            if (game.inPairs and len(players)<4) or len(players)<2:
                return Response({"status":'error',"message":"not enough players"},status=status.HTTP_409_CONFLICT)
            game_tools.startGame1(game.id,players)    
            serializerGame = GameRetrieveSerializer(game)
            playerSerializer = PlayerGameSerializer(players,many=True)
            PushNotificationConnector.push_notification(
                channel=f'mesa_{game.id}',
                event_name='start_game',
                data_notification={
                    'game_status': game.status,
                    'starter': data.starter,
                    'next_player': data.next_player,
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
            check = DataGame.objects.filter(filteres).filter(match__domino_game__id=game_id, active=True).exists()
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

        data_game = DataGame.objects.filter(active=True, match__domino_game__id = game.id).order_by('-id').first()
        
        if game.status in ["ru","fi"] and player.isPlaying and game.perPoints:
            have_points = game_tools.havepoints(data_game.match)
            if have_points:
                return Response({'status': 'error', "message":"The game is not over, wait until it's over."}, status=status.HTTP_409_CONFLICT)
        elif game.status in ["ru"] and player.isPlaying:
                return Response({'status': 'error', "message":"The game is not over, wait until it's over."}, status=status.HTTP_409_CONFLICT)
        
        players = game_tools.playersCount(data_game)
        exited = game_tools.exitPlayer(data_game,player,players,len(players))
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
        
        # game = DominoGame.objects.get(id=game_id)
        data_game = DataGame.objects.get(match__domino_game__id = game_id, active=True)

        game_tools.setWinner1(data_game,request.data["winner"])
        data_game.save()
        return Response({'status': 'success'}, status=200)
    
    @staticmethod
    def process_setstarter(request, game_id):
        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        # game = DominoGame.objects.get(id=game_id)
        data_game = DataGame.objects.get(match__domino_game__id = game_id, active=True)
        data_game.starter = request.data["starter"]
        data_game.save()
        
        return Response({'status': 'success'}, status=200)

    @staticmethod
    def process_setWinnerStarter(request, game_id):
        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        # game = DominoGame.objects.get(id=game_id)
        data_game = DataGame.objects.get(match__domino_game__id = game_id, active=True)
        data_game.starter = request.data["starter"]
        data_game.winner = request.data["winner"]
        data_game.save()
        return Response({'status': 'success'}, status=200)
    
    @staticmethod
    def process_setWinnerStarterNext(request, game_id):
        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        # game = DominoGame.objects.get(id=game_id)
        data_game = DataGame.objects.get(match__domino_game__id = game_id, active=True)
        game_tools.setWinnerStarterNext1(data_game,request.data["winner"],request.data["starter"],request.data["next_player"])
        data_game.save()
        return Response({'status': 'success'}, status=200)

    @staticmethod
    def process_setPatner(request, game_id):

        check_game = DominoGame.objects.filter(id = game_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"game not found"},status=status.HTTP_404_NOT_FOUND)    
        
        game = DominoGame.objects.get(id=game_id)
        data_game = DataGame.objects.filter(active=True, match__domino_game__id=game.id).order_by('-id').first()
        
        if data_game.player1.alias != request.data["alias"] and data_game.player2.alias != request.data["alias"] and data_game.player3.alias != request.data["alias"] and data_game.player4.alias != request.data["alias"]:
            return Response({"status":'error',"message":"The Player are not play in this game"},status=status.HTTP_409_CONFLICT)    
        
        players = game_tools.playersCount(data_game)
        # if game.inPairs and (game.payMatchValue > 0 or game.payWinValue > 0):
        #     return Response({'status': 'success'}, status=200)  
        # else:    
        for player in players:
            if player.alias == request.data["alias"]:
                patner = player
                break
        aux = data_game.player3
        if data_game.player2.alias == request.data["alias"]:
            data_game.player2 = aux
            data_game.player3 = patner
        elif data_game.player4.alias == request.data["alias"]:
            data_game.player4 = aux
            data_game.player3 = patner
        data_game.save()    
        return Response({'status': 'success'}, status=200) 