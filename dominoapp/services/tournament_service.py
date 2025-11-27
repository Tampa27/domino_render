import logging
from rest_framework import status
from rest_framework.response import Response
import pytz
from datetime import datetime, timezone
from django.db import transaction
from dominoapp.serializers import TournamentCreateSerializer
from dominoapp.models import Player, BlockPlayer, Tournament, Round
from dominoapp.utils.transactions import create_transactions
logger = logging.getLogger('django')


class TournamentService:
    
    @staticmethod
    def process_create(request):
        
        today = datetime.now(pytz.utc)
        start_date = pytz.timezone("UTC").localize(datetime.strptime(request.data.get('start_at'), "%d-%m-%Y %H:%M:%S"))
        deadline = pytz.timezone("UTC").localize(datetime.strptime(request.data.get('deadline'), "%d-%m-%Y %H:%M:%S"))
                
        if deadline <= today:
            return Response(data={
                "status": "error",
                "message": "Deadline must be a future date."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if start_date <= deadline:
            return Response(data={
                "status": "error",
                "message": "Start date must be after the deadline."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        request.data['start_at'] = start_date
        request.data['deadline'] = deadline
        
        serializer = TournamentCreateSerializer(data=request.data)
        try:
            if serializer.is_valid():
                serializer.save()
                return Response(data={
                    "status": "success",
                    "tournament": serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(data={
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.critical(f'Exception occurred while creating tournament: {str(e)}')
            return Response(data={
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_409_CONFLICT)
        
    @staticmethod
    def process_join(request, tournament_id):
        player = Player.objects.get(user__id=request.user.id)
                
        player.lastTimeInSystem = timezone.now()
        player.save()

        is_block = BlockPlayer.objects.filter(player_blocked__id=player.id).exists()
        if is_block:
            return Response({'status': 'error', "message":"These user is block, contact suport"}, status=status.HTTP_409_CONFLICT)

        check_game = Tournament.objects.filter(id = tournament_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"tournament not found"},status=status.HTTP_404_NOT_FOUND)    

        check_others_inscriptions = Tournament,object.filter(player_list__id = player.id).exist()

        if check_others_inscriptions:
            return Response({'status': 'error',"message":"El jugador ya está inscrito en un torneo."}, status=status.HTTP_409_CONFLICT)

        tournament = Tournament.objects.get(id=tournament_id)

        if player.total_coins < tournament.registration_fee:
            return Response({'status': 'error', "message":"No tienes suficientes monedas para inscribirte en el torneo."}, status=status.HTTP_409_CONFLICT)

        if datetime.now(timezone.utc) > tournament.deadline:
            return Response({'status': 'error', "message":"El plazo de inscripción para este torneo ha finalizado."}, status=status.HTTP_409_CONFLICT)

        with transaction.atomic():
            
            player.earned_coins -= tournament.registration_fee
            if player.earned_coins < 0:
                player.recharged_coins += player.earned_coins  # earned_coins is negative here
                player.earned_coins = 0            
            player.save()

            create_transactions(
                amount = tournament.registration_fee,
                from_user = player,
                type='gm',
                status='cp',
                descriptions=f"Inscripción al torneo {tournament.id}")

            tournament.player_list.add(player)
            tournament.save()
        return Response({'status': 'success', "message":"Te has inscrito correctamente en el torneo."}, status=status.HTTP_200_OK)

    @staticmethod
    def process_order_players_rounds(tournament:Tournament):
        players = tournament.player_list.all()        
        number_of_players = players.count()
        half_players = number_of_players // 2

        round = Round.objects.create(
            tournament = tournament
        )
        round.player_list.add(*players)

        ### Crear las mesas y asignar los jugadores
        # for branch_number in range(1, (half_players // 4) + 1):
        #     branch = Branch.objects.create(
        #         round=round,
        #         branch_number=branch_number
        #     )
        #     branch_players = players[(branch_number - 1) * 8: branch_number * 8]
        #     branch.player_list.add(*branch_players)
        #     branch.save()



        return