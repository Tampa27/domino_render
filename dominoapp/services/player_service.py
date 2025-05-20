from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework import status
from rest_framework.response import Response
from django.db.models import Q
from django.contrib.auth.models import User
from dominoapp.models import Player, DominoGame
from dominoapp.serializers import PlayerSerializer, PlayerLoginSerializer
from dominoapp.connectors.google_verifier import GoogleTokenVerifier

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
            # Verifica el token de Google
            google_user, error = GoogleTokenVerifier.verify(token)
            
            if error:
                return Response(
                        {"status":'error',
                        "message": str(error)}, 
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            
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
                    name = google_user['name'],
                    photo_url = google_user.get('picture', None),
                    alias= google_user['email'].split('@')[0],
                    user= user
                )
            else:
                player = Player.objects.get(email=google_user['email'])
            
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
            return Response(
                {"status":'error',
                 "message": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )