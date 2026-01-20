import os
import logging
from rest_framework import status
from rest_framework.response import Response
import pytz
from datetime import datetime, timezone
from django.db import transaction
from dominoapp.serializers import TournamentCreateSerializer
from dominoapp.models import Player, BlockPlayer, Tournament, Round, Pair, DominoGame, Match_Game, Bank
from dominoapp.utils.transactions import create_transactions
from dominoapp.utils.fcm_message import FCMNOTIFICATION
logger = logging.getLogger('django')


class TournamentService:
    
    @staticmethod
    def process_create(request):
        user = request.user
        timezone = 'America/Havana'
        try:
            player = Player.objects.get(user__id = user.id)
            timezone = player.timezone
        except:
            pass
        today = datetime.now(pytz.utc)
        start_date = pytz.timezone(timezone).localize(datetime.strptime(request.data.get('start_at'), "%d-%m-%Y %H:%M:%S")).astimezone(pytz.utc)
        deadline = pytz.timezone(timezone).localize(datetime.strptime(request.data.get('deadline'), "%d-%m-%Y %H:%M:%S")).astimezone(pytz.utc)
                
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
        
        try:
            request.data['start_at'] = start_date
            request.data['deadline'] = deadline
        except:
            request.data._mutable = True
            request.data['start_at'] = start_date
            request.data['deadline'] = deadline
            request.data._mutable = False
        try:
            pay_percent = int(os.getenv("TOURNAMENT_ADMIN_PERCENT"))
        except Exception as error:
            logger.critical("El porciento de ganancias no esta definido")
            return Response(data={
                "status": "error",
                "message": "Algo esta mal vuelva a intantar."
            }, status=status.HTTP_409_CONFLICT)
        
        if "winner_payout" in request.data and int(request.data["winner_payout"])>0:
            pay_percent += int(request.data["winner_payout"])

            if "second_payout" in request.data and int(request.data["second_payout"])>0:
                pay_percent += int(request.data["second_payout"])
                
            if "third_payout" in request.data and int(request.data["third_payout"])>0:
                pay_percent += int(request.data["third_payout"])
                
            if pay_percent != 100:
                return Response(data={
                    "status": "error",
                    "message": "El porciento de las ganancias no suma 100."
                }, status=status.HTTP_400_BAD_REQUEST) 
        
        if "min_player" in request.data:
            if int(request.data["min_player"])<8:
                return Response(data={
                    "status": "error",
                    "message": f"El número mínimo de jugadores es 8."
                }, status=status.HTTP_400_BAD_REQUEST)
            if "max_player" in request.data and int(request.data["max_player"])<int(request.data["min_player"]):
                return Response(data={
                    "status": "error",
                    "message": f"El número máximo de jugadores debe ser mayor que el valor mínimo {request.data["min_player"]}."
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            if "max_player" in request.data and int(request.data["max_player"])<8:
                return Response(data={
                    "status": "error",
                    "message": "El número máximo de jugadores debe ser mayor que el valor mínimo 8."
                }, status=status.HTTP_400_BAD_REQUEST) 
        
        if "number_match_win" in request.data and int(request.data["number_match_win"]) <= 0:
            return Response(data={
                "status": "error",
                "message": f"El número de partidos a ganar debe ser mayor que 0."
            }, status=status.HTTP_400_BAD_REQUEST)
        
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
                
        player.lastTimeInSystem = datetime.now()
        player.save()

        is_block = BlockPlayer.objects.filter(player_blocked__id=player.id).exists()
        if is_block:
            return Response({'status': 'error', "message":"These user is block, contact suport"}, status=status.HTTP_409_CONFLICT)

        check_game = Tournament.objects.filter(id = tournament_id).exists()
        if not check_game:
            return Response({"status":'error',"message":"tournament not found"},status=status.HTTP_404_NOT_FOUND)    

        check_others_inscriptions = Tournament.objects.filter(active=True, player_list__id = player.id).exists()

        if check_others_inscriptions:
            return Response({'status': 'error',"message":"El jugador ya está inscrito en un torneo."}, status=status.HTTP_409_CONFLICT)

        tournament = Tournament.objects.get(id=tournament_id)

        if not tournament.active:
            return Response({"status":'error',"message":"Este torneo aun no esta activo"},status=status.HTTP_409_CONFLICT)
        
        if player.total_coins < tournament.registration_fee:
            return Response({'status': 'error', "message":"No tienes suficientes monedas para inscribirte en el torneo."}, status=status.HTTP_409_CONFLICT)

        if datetime.now(timezone.utc) > tournament.deadline:
            return Response({'status': 'error', "message":"El plazo de inscripción para este torneo ha finalizado."}, status=status.HTTP_409_CONFLICT)

        if int(tournament.player_list.count()) == int(tournament.max_player):
                return Response({'status': 'error', "message":"Ya el torneo alcanzó el máximo número de jugadores."}, status=status.HTTP_409_CONFLICT)
                
        with transaction.atomic():
            tournament.player_list.add(player)
            tournament.save()
            
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
            
        return Response({'status': 'success', "message":"Te has inscrito correctamente en el torneo."}, status=status.HTTP_200_OK)

    @staticmethod
    def process_order_players_rounds(tournament:Tournament, round:Round=None):
        players = tournament.player_list.all()      

        if round is None:
            round = Round.objects.create(
                tournament = tournament
            )
            round.player_list.add(*players)
            players_list = list(round.player_list.order_by("?"))
            number_of_players = len(players_list)
            half_players = number_of_players//2

            ### Crear las mesas y asignar los jugadores
            for i in range(0, half_players):
                pair = Pair.objects.create(
                    player1 = players_list[i],
                    player2 = players_list[number_of_players-1-i]
                )
                round.pair_list.add(pair)
            
            tournament.status = "ready"
            tournament.save(update_fields=['status'])
        else:
            new_round = Round.objects.create(
                tournament = tournament
            )
            new_round.pair_list.add(*round.winner_pair_list.all())
            pair_list = list(new_round.pair_list.all())
            for pair in pair_list:
                new_round.player_list.add(pair.player1)
                new_round.player_list.add(pair.player2)
            round = new_round
        
        total_pair = round.pair_list.all().count()
        pair_list = round.pair_list.all()
        if total_pair % 2 != 0:
            last_pair = pair_list.last()
            pair_list = pair_list.exclude(id = last_pair.id)
            round.winner_pair_list.add(last_pair)
            total_pair -= 1

        pair_list = list(pair_list)
        for i in range(0, total_pair, 2):
            game = DominoGame.objects.create(
                player1 = pair_list[i].player1,
                player3 = pair_list[i].player2,
                player2 = pair_list[i+1].player1,
                player4 = pair_list[i+1].player2,
                variant= tournament.variant,
                status = "ready",
                maxScore = tournament.maxScore,
                inPairs = True,
                perPoints = True,
                startWinner= tournament.startWinner,
                moveTime= tournament.moveTime,
                password = f"{tournament.id}-{round.id}",
                tournament = tournament
            )
            round.game_list.add(game)
            match = Match_Game.objects.create(
                game = game
            )
            match.player_list.add(pair_list[i].player1)
            match.player_list.add(pair_list[i].player2)
            match.player_list.add(pair_list[i+1].player1)
            match.player_list.add(pair_list[i+1].player2)
            match.pair_list.add(pair_list[i])
            match.pair_list.add(pair_list[i+1])
   
    @staticmethod
    def process_pay_winners(tournament:Tournament, winner: Pair, second: Pair= None, third: Pair= None):
        tournament.first_place_object_id = winner.id
                
        total_player = tournament.player_list.count()            
        total_registration_fee = tournament.registration_fee*total_player
        
        if tournament.winner_payout > 0:
            
            try:
                bank = Bank.objects.all().first()
            except:
                bank = Bank.objects.create()
            
            TRANSFER_PERCENT = os.getenv("TOURNAMENT_ADMIN_PERCENT")
            bank_amount = int(total_registration_fee*int(TRANSFER_PERCENT)/100)
            
            bank.tournament_coins += bank_amount
            bank.save(update_fields=["tournament_coins"])
            
            player_coins = int((total_registration_fee*tournament.winner_payout/100)/2)
            
            winner.player1.earned_coins+= player_coins
            winner.player1.save(update_fields=["earned_coins"])
            winner.player2.earned_coins+= player_coins
            winner.player2.save(update_fields=["earned_coins"])
            
            ## Crear las transacciones
            create_transactions(
                amount=player_coins,
                to_user= winner.player1,
                status= "cp",
                type= "gm",
                descriptions=f"Por terminar en 1er lugar en el torneo {tournament.id}"
            )

            FCMNOTIFICATION.send_fcm_message(
                user= winner.player1.user,
                title= "🏅 Campeón del Torneo",
                body=f"¡1er lugar en Dominó Club! 🥇 Premio: {player_coins} monedas. ¡Felicidades! 🎉"
            )
            create_transactions(
                amount=player_coins,
                to_user= winner.player2,
                status= "cp",
                type= "gm",
                descriptions=f"Por terminar en 1er lugar en el torneo {tournament.id}"
            )
            FCMNOTIFICATION.send_fcm_message(
                user= winner.player2.user,
                title= "🏅 Campeón del Torneo",
                body=f"¡1er lugar en Dominó Club! 🥇 Premio: {player_coins} monedas. ¡Felicidades! 🎉"
            )

        if second:
            tournament.second_place_object_id = second.id

            if tournament.second_payout > 0:
                player_coins = int((total_registration_fee*tournament.second_payout/100)/2)
            
                second.player1.earned_coins+= player_coins
                second.player1.save(update_fields=["earned_coins"])
                second.player2.earned_coins+= player_coins                
                second.player2.save(update_fields=["earned_coins"])
                
                ## Crear las transacciones
                create_transactions(
                    amount=player_coins,
                    to_user= second.player1,
                    status= "cp",
                    type= "gm",
                    descriptions=f"Por terminar en 2do lugar en el torneo {tournament.id}"
                )
                FCMNOTIFICATION.send_fcm_message(
                    user= second.player1.user,
                    title= "🎊 Subcampeón del Torneo",
                    body=f"¡2do lugar en Dominó Club! 🥈 Premio: {player_coins} monedas. ¡Sigue así! ⭐"
                )
                create_transactions(
                    amount=player_coins,
                    to_user= second.player2,
                    status= "cp",
                    type= "gm",
                    descriptions=f"Por terminar en 2do lugar en el torneo {tournament.id}"
                )
                FCMNOTIFICATION.send_fcm_message(
                    user= second.player2.user,
                    title= "🎊 Subcampeón del Torneo",
                    body=f"¡2do lugar en Dominó Club! 🥈 Premio: {player_coins} monedas. ¡Sigue así! ⭐"
                )
                
        if third:
            tournament.third_place_object_id = third.id
            
            if tournament.third_payout > 0:
                player_coins = int((total_registration_fee*tournament.third_payout/100)/2)
            
                third.player1.earned_coins+= player_coins
                third.player1.save(update_fields=["earned_coins"])
                third.player2.earned_coins+= player_coins
                third.player2.save(update_fields=["earned_coins"])
                
                ## Crear las transacciones
                create_transactions(
                    amount=player_coins,
                    to_user= third.player1,
                    status= "cp",
                    type= "gm",
                    descriptions=f"Por terminar en 3er lugar en el torneo {tournament.id}"
                )
                FCMNOTIFICATION.send_fcm_message(
                    user= third.player1.user,
                    title= "👍 ¡Felicitaciones!",
                    body=f"¡3er lugar en Dominó Club! 🥉 Premio: {player_coins} monedas. ¡Felicitaciones!"
                )
                create_transactions(
                    amount=player_coins,
                    to_user= third.player2,
                    status= "cp",
                    type= "gm",
                    descriptions=f"Por terminar en 3er lugar en el torneo {tournament.id}"
                )
                FCMNOTIFICATION.send_fcm_message(
                    user= third.player2.user,
                    title= "👍 ¡Felicitaciones!",
                    body=f"¡3er lugar en Dominó Club! 🥉 Premio: {player_coins} monedas. ¡Felicitaciones!"
                )
        
        tournament.save(update_fields=["first_place_object_id", "second_place_object_id", "third_place_object_id"])