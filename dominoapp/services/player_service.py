import os
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.db.models import Q, F, ExpressionWrapper, FloatField, Case, When, Value
from django.contrib.auth.models import User
from django.utils import timezone
from django.shortcuts import redirect
from fcm_django.models import FCMDevice
from dominoapp.models import Player, DominoGame, BlockPlayer, AppVersion, ReferralPlayers
from dominoapp.serializers import PlayerSerializer, PlayerLoginSerializer, PlayerRankinSerializer
from dominoapp.connectors.google_verifier import GoogleTokenVerifier
from dominoapp.connectors.discord_connector import DiscordConnector
from dominoapp.utils.constants import ApiConstants
from dominoapp.utils.players_tools import get_device_hash
import logging
logger = logging.getLogger('django')

class PlayerService:

    @staticmethod
    def process_retrieve(request, player_id):
        check_player = Player.objects.filter(id = player_id).exists()
        if not check_player:
            return Response({"status":'error',"message":"player not found"},status=status.HTTP_404_NOT_FOUND)    
        
        result = Player.objects.get(id = player_id)
        serializer = PlayerSerializer(result)

        game = DominoGame.objects.filter(
                Q(player1__alias = result.alias)|
                Q(player2__alias = result.alias)|
                Q(player3__alias = result.alias)|
                Q(player4__alias = result.alias)
                )
        game_id = None
        if game.exists():
            game_id = game.first().id
    
        return Response({'status': 'success', "player":serializer.data,"game_id":game_id}, status=status.HTTP_200_OK)
    
    @staticmethod
    def process_create(request):
        serializer = PlayerSerializer(data=request.data)  
        if serializer.is_valid():  
            serializer.save()  
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)  
        else:  
            return Response({"status": "error", "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
    @staticmethod
    def process_update(request, player_id, is_partial):
        check_player = Player.objects.filter(id = player_id, user__id = request.user.id).exists()
        if not check_player:
            return Response({"status":'error',"message":"player not found"},status=status.HTTP_404_NOT_FOUND)    
        
        result = Player.objects.get(id=player_id)  
        serializer = PlayerSerializer(result, data = request.data, partial=is_partial)
        if serializer.is_valid():  
            serializer.save()  
            return Response({"status": "success", "data": serializer.data})  
        else:  
            return Response({"status": "error", "data": serializer.errors}, status= status.HTTP_400_BAD_REQUEST)  
    
    @staticmethod
    def process_delete(request, player_id):
        check_player = Player.objects.filter(id = player_id, user__id = request.user.id).exists()
        if not check_player:
            return Response({"status":'error',"message":"player not found"},status=status.HTTP_404_NOT_FOUND)    
        
        result = Player.objects.get(id=player_id)  
        result.delete()  
        return Response({"status": "success", "message": "Record Deleted"})    
    
    @staticmethod
    def process_login(request):
        token = request.data.get('token')

        try:
            google_user, error = GoogleTokenVerifier.verify(token)
            
            if error:
                return Response(
                        {"status":'error',
                        "message": str(error)}, 
                        status=status.HTTP_401_UNAUTHORIZED
                    )
        except Exception as e:
            return Response(
                {"status":'error',
                 "message": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            with transaction.atomic():
                is_block = BlockPlayer.objects.filter(player_blocked__email=google_user['email']).exists()
                if is_block:
                    return Response({'status': 'error', "message":"These user is block, contact suport"}, status=status.HTTP_409_CONFLICT)
                
                exist = Player.objects.filter(email=google_user['email']).exists()
                
                if not exist:
                    # Busca o crea el usuario
                    user, created = User.objects.get_or_create(
                            email=google_user['email'],
                            defaults={
                                'username': google_user['email'].split('@')[0],
                                'is_active': True
                            }
                        )

                    player = Player.objects.create(
                        email=google_user['email'],                    
                        alias= google_user['email'].split('@')[0],
                        user= user
                    )

                    if "refer_code" in request.data:
                        try:
                            referral_model = Player.objects.get(referral_code = request.data["refer_code"], inactive_player=False)
                        except:
                            referral_model = None
                        if referral_model:
                            player.parent = referral_model
                            player.save(update_fields=['parent'])
                    else:
                        hash_sha256 = get_device_hash(request)
                        print(f"SHA-256: {hash_sha256}")
                        
                        try:
                            referral_model = ReferralPlayers.objects.get(referral_code=hash_sha256)
                        except:
                            referral_model = None
                        if referral_model:
                            player.parent = referral_model.referrer_player
                            player.save(update_fields=['parent'])
                            
                            referral_model.delete()  # Elimina el modelo de referencia una vez usado      
                    
                    DiscordConnector.send_event(
                        ApiConstants.AdminNotifyEvents.ADMIN_EVENT_NEW_USER.key,
                        {
                            "email": google_user['email'],
                            "name" : google_user['name']
                        }
                    )
                    
                else:
                    player = Player.objects.get(email=google_user['email'])

                photo_profile = google_user.get('picture', None)
                if not photo_profile:
                    photo_profile = os.getenv('URL_PROFILE_PHOTO')
                
                player.name = google_user['name']
                player.photo_url = photo_profile
                player.lastTimeInSystem = timezone.now()
                player.inactive_player = False
                player.send_delete_email = False
                player.save(update_fields=['name', 'photo_url','lastTimeInSystem','inactive_player', 'send_delete_email'])

                # Para registrar un dispositivo
                fcm_token = request.data.get("fcm_token")
                if fcm_token:
                    FCMDevice.objects.update_or_create(
                        registration_id = fcm_token,
                        defaults={
                            "user": player.user,  # asociar a un usuario
                            "type": "android",  # o "ios", "web"
                        }
                    )

                # Genera tokens JWT usando simplejwt
                refresh = RefreshToken.for_user(player.user)

                player_data = PlayerLoginSerializer(player).data            
                player_data["is_new"] = (not exist)

                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': player_data
                })
        except Exception as e:
            logger.critical(f"No se completo la creación del player {google_user['email']}. Error => {str(e)}")
            
            return Response(
                {"status":'error',
                 "message": str(e)}, 
                status=status.HTTP_409_CONFLICT
            )  
        
    @staticmethod
    def process_fcm_register(request):
        try:            
            # Para registrar un dispositivo
            fcm_token = request.data.get("fcm_token")
            if str(fcm_token).strip() == "":
                return Response(
                    {"status":'error',
                     "message": "fcm_token is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            FCMDevice.objects.update_or_create(
                registration_id = fcm_token,
                defaults={
                    "user": request.user,  # asociar a un usuario
                    "type": "android",  # o "ios", "web"
                }
            )
        except Exception as error:
            logger.error(f"Error creating FCM Device for user {request.user.username}, Error->: {str(error)}")
            
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    @staticmethod
    def process_refer_code(request):
        try:
            referrer_player = Player.objects.get(user__id = request.user.id)
        except:
            return Response("Player not found", status= status.HTTP_404_NOT_FOUND)

        BACKEND_URL = os.getenv("BACKEND_URL", "localhost:8000/v2/api")
        
        return Response(data={
            "refer_code" : referrer_player.referral_code,
            "url": f"{BACKEND_URL}/refer/?refer_code={referrer_player.referral_code}"
        }, status= status.HTTP_200_OK)
        
    @staticmethod
    def process_refer_register(request):
        referrer_player = None
        try:
            refer_code = request.query_params.get('refer_code', None)
            referrer_player = Player.objects.get(referral_code = refer_code, inactive_player=False)
        except:
            pass
        
        if referrer_player:
            hash_sha256 = get_device_hash(request)
            print(f"SHA-256: {hash_sha256}")
            
            try:
                ReferralPlayers.objects.update_or_create(
                    referral_code=hash_sha256,
                    defaults={
                        "referrer_player": referrer_player
                    }
                )
            except Exception as error:
                logger.error(f"Error creating referral player: {str(error)}")
                pass
            
        
        app = AppVersion.objects.first()
        if app and app.store_link:
            return redirect(app.store_link)
        
        return redirect('https://dominoclub.online/')
    
    @staticmethod
    def process_rankin(request):
        paginator = PageNumberPagination()
        
        page_size = request.query_params.get("page_size", 100)
        order_by = request.query_params.get("ordering", None)
        
        paginator.page_size = page_size  # Items por página
        
        queryset = Player.objects.all()
        if order_by in ['elo', '-elo']:
            queryset = queryset.exclude(elo=1500).order_by(order_by)
        elif order_by in ['data_percent', '-data_percent']:
            queryset = queryset.annotate(
                total_games=F('dataWins') + F('dataLoss'),
                data_percent=Case(
                    When(total_games=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('dataWins') * 100.0 / F('total_games'),
                        output_field=FloatField()
                    ),
                    output_field=FloatField()
                )
            ).filter(total_games__gte = 100).order_by(order_by)
        elif order_by in ['match_percent', '-match_percent']:
            queryset = queryset.annotate(
                total_games=F('matchWins') + F('matchLoss'),
                match_percent=Case(
                    When(total_games=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('matchWins') * 100.0 / F('total_games'),
                        output_field=FloatField()
                    ),
                    output_field=FloatField()
                )
            ).filter(total_games__gte = 20).order_by(order_by)
        elif order_by in ['coins', '-coins']:
            queryset = queryset.annotate(
                coins=F('earned_coins') + F('recharged_coins')
            ).order_by(order_by)
            
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = PlayerRankinSerializer(result_page, many=True)
        
        return paginator.get_paginated_response(serializer.data)