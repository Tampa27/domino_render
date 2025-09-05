import shortuuid
import os
from rest_framework import status
from rest_framework.response import Response
from django.db.models import Q, Sum, OuterRef, Subquery
from django.http import HttpResponse
from datetime import datetime, timedelta
from dominoapp.models import Player, Bank, Transaction, Status_Payment, Status_Transaction, BankAccount
from dominoapp.utils.transactions import create_reload_transactions, create_extracted_transactions, create_promotion_transactions
from dominoapp.utils.constants import ApiConstants
from dominoapp.utils.pdf_helpers import create_resume_game_pdf
from dominoapp.utils.fcm_message import FCMNOTIFICATION
from dominoapp.connectors.discord_connector import DiscordConnector
from dominoapp.connectors.paypal_connector import PayPalConnector


class PaymentService:

    @staticmethod
    def process_recharge(request):

        check_player = Player.objects.filter(alias=request.data["alias"]).exists()
        if not check_player:
            return Response(data={'status': 'error', "message":'Player not found'}, status=status.HTTP_404_NOT_FOUND)

        player = Player.objects.get(alias=request.data["alias"])
        player.recharged_coins+= int(request.data["coins"])
        player.save(update_fields=["recharged_coins"])

        try:
            bank = Bank.objects.all().first()
        except:
            bank = Bank.objects.create()
        
        if player.parent and not player.reward_granted:
            try:
                player.parent.earned_coins += ApiConstants.REFER_REWARD
                player.parent.save(update_fields=["earned_coins"])

                player.reward_granted = True
                player.save(update_fields=["reward_granted"])

                create_promotion_transactions(
                    amount= ApiConstants.REFER_REWARD,
                    from_user=player,
                    to_user= player.parent,
                    status="cp",
                    descriptions=f"El player {player.parent.alias} ha ganado {ApiConstants.REFER_REWARD} por el referido {player.alias}."
                )
                
                bank.promotion_coins+=int(ApiConstants.REFER_REWARD)
                bank.save(update_fields=['promotion_coins'])
                
                FCMNOTIFICATION.send_fcm_message(
                user = player.parent.user,
                title = "Nueva Recarga en Domino Club",
                body = f"{player.parent.name} usted a recibido una recarga en su cuenta de Domino Club con {ApiConstants.REFER_REWARD} monedas, por haber referenciado al player {player.name}."
                )
                DiscordConnector.send_event(
                    "Promoción",
                    {
                        'player': str(player.parent.alias),
                        "amount": ApiConstants.REFER_REWARD,
                        "referred_user": str(player.alias)
                    }
                )   
            except:
                pass

        bank.buy_coins+=int(request.data["coins"])
        bank.save(update_fields=['buy_coins'])

        try:
            admin = Player.objects.get(user__id = request.user.id)
        except:
            admin = None
        
        transaction = Transaction.objects.filter(
            to_user__alias=request.data["alias"], type='rl'
        ).annotate(
            latest_status_name=Subquery(
                Status_Transaction.objects.filter(status_transaction=OuterRef('pk')
        ).order_by('-created_at').values('status')[:1])
        ).filter(latest_status_name='p').order_by('-time').first()
        
        if transaction:
            transaction.amount = int(request.data["coins"])
            transaction.admin = admin
            transaction.paymentmethod=request.data.get('paymentmethod', None)
            transaction.save(update_fields=['amount', 'admin', 'paymentmethod'])
            new_status = Status_Transaction.objects.create(status = 'cp')
            transaction.status_list.add(new_status)
        else:
            create_reload_transactions(
                to_user=player, amount=int(request.data["coins"]), status="cp", 
                admin=admin,
                external_id=request.data.get('external_id', None),
                paymentmethod=request.data.get('paymentmethod', None)
                )
    
        FCMNOTIFICATION.send_fcm_message(
            user = player.user,
            title = "Nueva Recarga en Domino Club",
            body = f"{player.name} usted a recargado su cuenta en Domino Club con {request.data['coins']} monedas."
            )
        DiscordConnector.send_event(
            ApiConstants.AdminNotifyEvents.ADMIN_EVENT_NEW_RELOAD.key,
            {
                'player': request.data["alias"],
                "amount": request.data["coins"]
            }
        )
        
        return Response({'status': 'success', "message":'Balance recharged'}, status=status.HTTP_200_OK)
    
    @staticmethod
    def process_request_recharge(request):
        try:
            player = Player.objects.get(user__id=request.user.id)
        except:
            return Response(data={'status': 'error', "message":"User not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
               
        
        create_reload_transactions(
            to_user=player, amount=int(request.data["coins"]), status="p",
            )
        
        transaction_id= shortuuid.random(length=6)
        
        send_request = DiscordConnector.send_transaction_request(
            ApiConstants.AdminNotifyEvents.ADMIN_EVENT_NEW_RELOAD.key,
            {   
                'player_name': player.name,
                'player_alias': player.alias,
                'amount': request.data["coins"],
                'player_phone': request.data["phone"],
                'transaction_id': transaction_id
            }
        )
        if send_request:
            return Response({'status': 'success', "transaction_id": transaction_id
            }, status=status.HTTP_200_OK)
        
        return Response({'status': 'error', "message":'Your request could not be processed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @staticmethod
    def process_promotions(request):

        check_player = Player.objects.filter(alias=request.data["alias"]).exists()
        if not check_player:
            return Response(data={'status': 'error', "message":'Player not found'}, status=status.HTTP_404_NOT_FOUND)

        player = Player.objects.get(alias=request.data["alias"])
        player.recharged_coins+= int(request.data["coins"])
        player.save(update_fields=["recharged_coins"])

        try:
            bank = Bank.objects.all().first()
        except:
            bank = Bank.objects.create()

        bank.promotion_coins+=int(request.data["coins"])
        bank.save(update_fields=['promotion_coins'])  

        try:
            admin = Player.objects.get(user__id = request.user.id)
        except:
            admin = None
        
        create_promotion_transactions(
            amount= int(request.data["coins"]),
            to_user= player,
            status="cp",
            admin=admin
        )
        
        DiscordConnector.send_event(
            "Promoción",
            {
                'player': request.data["alias"],
                "amount": request.data["coins"]
            }
        )
        
        return Response({'status': 'success', "message":'Balance recharged'}, status=status.HTTP_200_OK)
    
    @staticmethod
    def process_extract(request):

        check_player = Player.objects.filter(alias=request.data["alias"]).exists()
        if not check_player:
            return Response(data={'status': 'error', "message":'Player not found'}, status=status.HTTP_404_NOT_FOUND)

        player = Player.objects.get(alias=request.data["alias"])

        try:
            admin = Player.objects.get(user__id = request.user.id)
        except:
            admin = None
        
                
        transaction = Transaction.objects.filter(
            from_user__alias=request.data["alias"], type='ex'
        ).annotate(
            latest_status_name=Subquery(
                Status_Transaction.objects.filter(status_transaction=OuterRef('pk')
        ).order_by('-created_at').values('status')[:1])
        ).filter(latest_status_name='p').order_by('-time').first()
        
        if transaction:
            transaction.amount = int(request.data["coins"])
            transaction.admin = admin
            transaction.paymentmethod=request.data.get('paymentmethod', None)
            transaction.save(update_fields=['amount', 'admin', 'paymentmethod'])
            new_status = Status_Transaction.objects.create(status = 'cp')
            transaction.status_list.add(new_status)
        else:
            if player.total_coins < int(request.data["coins"]):
                return Response(data={'status': 'error', "message":"You don't have enough amount"}, status=status.HTTP_409_CONFLICT)
            
            player.earned_coins -= int(request.data["coins"])
            if player.earned_coins<0:
                player.recharged_coins += player.earned_coins
                player.earned_coins = 0

            player.save(update_fields=['earned_coins', 'recharged_coins'])
            
            try:
                bank = Bank.objects.all().first()
            except:
                bank = Bank.objects.create()

            bank.extracted_coins+=int(request.data["coins"])
            bank.save(update_fields=['extracted_coins'])

            create_extracted_transactions(
                from_user=player, amount=int(request.data["coins"]), status="cp",
                admin=admin,
                external_id=request.data.get('external_id', None),
                paymentmethod=request.data.get('paymentmethod', None)
                )
            
        FCMNOTIFICATION.send_fcm_message(
            user = player.user,
            title = "Nueva Extracción en Domino Club",
            body = f"Felicidades {player.name} 🎉, usted a extraido {request.data['coins']} monedas de su cuenta en Domino Club."
            )

        DiscordConnector.send_event(
            ApiConstants.AdminNotifyEvents.ADMIN_EVENT_NEW_EXTRACTION.key,
            {
                'player': request.data["alias"],
                "amount": request.data["coins"]
            }
        )
        
        return Response({'status': 'success', "message":'Balance recharged'}, status=status.HTTP_200_OK)
    
    @staticmethod
    def process_request_extraction(request):
        try:
            player = Player.objects.get(user__id=request.user.id)
        except:
            return Response(data={'status': 'error', "message":"User not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        
        min_extraction = int(os.environ.get('MIN_EXTRACTION',800))
        
        if player.total_coins < min_extraction:
            return Response(data={'status': 'error', "message":"You don't have enough amount"}, status=status.HTTP_409_CONFLICT)
        
        if player.total_coins < int(request.data["coins"]):
            return Response(data={'status': 'error', "message":"You don't have enough amount"}, status=status.HTTP_409_CONFLICT)
        
        try:
            bankaccount = BankAccount.objects.get(player__id = player.id, account_number=request.data["card_number"])
            if bankaccount and str(bankaccount.phone) != (request.data["phone"]):
                bankaccount.phone = request.data["phone"]
                bankaccount.save(update_fields=['phone'])
        except:
            bankaccount = BankAccount.objects.create(
                player = player, 
                account_number=request.data["card_number"],
                phone = request.data["phone"]
                )
               
        create_extracted_transactions(
            from_user=player, amount=int(request.data["coins"]), status="p",
            bankaccount=bankaccount
            )

        transaction_id= shortuuid.random(length=6)
        send_request = DiscordConnector.send_transaction_request(
            ApiConstants.AdminNotifyEvents.ADMIN_EVENT_NEW_EXTRACTION.key,
            {   
                'player_name': player.name,
                'player_alias': player.alias,
                'amount': request.data["coins"],
                'coins':request.data["coins"],
                'card_number': request.data["card_number"],
                'player_phone': request.data["phone"],
                'transaction_id': transaction_id
            }
        )
        
        if send_request:
            player.earned_coins -= int(request.data["coins"])
            if player.earned_coins<0:
                player.recharged_coins += player.earned_coins
                player.earned_coins = 0
            player.save(update_fields=['earned_coins', 'recharged_coins'])
            
            try:
                bank = Bank.objects.all().first()
            except:
                bank = Bank.objects.create()

            bank.extracted_coins+=int(request.data["coins"])
            bank.save(update_fields=['extracted_coins'])
            
            return Response({'status': 'success', "transaction_id": transaction_id
                }, status=status.HTTP_200_OK)
        
        return Response({'status': 'error', "message":'Your request could not be processed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
      
    @staticmethod
    def process_resume_game(request):
        alias = request.query_params.get('alias', None)
        game_id = request.query_params.get('game_id', None)
        from_at_str = request.query_params.get('from_at', None)
        to_at_str = request.query_params.get('to_at', None)
        traceback = request.query_params.get('traceback', False)

        if not alias:
            return Response(data={
                'status': 'success',
                "message": "Nothing to summarize"
            }, status=status.HTTP_200_OK)
        
        try:
            player = Player.objects.get(alias = alias)
        except:
            return Response(data={
                    'status': 'success',
                    "message": "Nothing to summarize"
                }, status=status.HTTP_200_OK)

        requets_filters = (Q(from_user__alias = alias) | Q(to_user__alias = alias))
        if game_id:
            requets_filters &= Q(game__id = game_id)
        
        formats = [
            "%d-%m-%Y %H:%M:%S",  # 12-06-2025 11:47:10
            "%d-%m-%Y %H:%M",       # 12-06-2025 11:47
            "%d-%m-%Y %H",          # 12-06-2025 11
            "%d-%m-%Y",             # 12-06-2025
        ]        
        if from_at_str:
            for fmt in formats:
                try:
                    from_at = datetime.strptime(from_at_str, fmt)
                except:
                    continue
            requets_filters &= Q(time__gte = from_at)
        if to_at_str:
            for fmt in formats:
                try:
                    to_at = datetime.strptime(to_at_str, fmt)
                except:
                    continue
            requets_filters &= Q(time__lte = to_at)
                
        queryset = Transaction.objects.filter(type='gm').filter(requets_filters).order_by("game")

        list_games = queryset.values("game").distinct("game")

        queryset = queryset.order_by("time")
        
        total_amount_win = 0
        total_amount_loss = 0
        totals_list_games = []
        for game_element in list_games:
            game_transactions = queryset.filter(game__id = game_element["game"])
            amount_win = game_transactions.exclude(to_user__isnull=True).aggregate(total=Sum('amount'))['total'] or 0
            amount_loss = game_transactions.exclude(from_user__isnull=True).aggregate(total=Sum('amount'))['total'] or 0
            total_amount_win += amount_win
            total_amount_loss += amount_loss
            dict_resume = {
                "game_id" : game_element["game"],
                "totals_games": 0,
                "amount_win": amount_win,
                "amount_loss": amount_loss,
                "balance": amount_win - amount_loss
            }
            for trans in game_transactions:
                if trans.descriptions:
                    description_list = trans.descriptions.split(" ")
                    if ("gane" in description_list) or ("perdi" in description_list) or ("salir" in description_list):
                        dict_resume["totals_games"] += 1 
                else:
                    pass
            
            totals_list_games.append(dict_resume)
        
        transaction_data = {
                "player_name": player.name if player else " ",
                "player_alias": player.alias if player else " ",
                "player_coins": (player.recharged_coins + player.earned_coins) if player else 0,
                "from_day": (queryset.first().time - timedelta(hours=4)).strftime('%d/%m/%Y  %H:%M:%S'),
                "to_day": (queryset.last().time - timedelta(hours=4)).strftime('%d/%m/%Y  %H:%M:%S'),
                "total_amount_win": str(total_amount_win),
                "total_amount_loss": str(total_amount_loss),
                "total_balance": str(total_amount_win - total_amount_loss),
                "list_games": totals_list_games,
                "traceback": queryset if traceback else None
            }


        pdf_out = create_resume_game_pdf(transaction_data)

        response = HttpResponse(pdf_out, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="'+ 'model_'+str(player.alias)+'.pdf"'
        return response
    
    @staticmethod
    def process_payment(request):
        try:
            user = Player.objects.get(user__id = request.user.id)
        except:
            return Response(data={'status': 'error', "message":'Player not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if str(request.data['amount']) < str(1):
            return Response(data={'status': 'error', "message":'The amount must be greater than 0.'}, status=status.HTTP_409_CONFLICT)

        response, error = PayPalConnector.create_payment(amount = request.data['amount'], user_email= user.email)

        if error:
            return error
        
        if response["status"] == "success":
            return Response(data = response, status=status.HTTP_200_OK)
        else:
            return Response(data = response, status=status.HTTP_400_BAD_REQUEST)
    
    @staticmethod
    def process_paypal_capture(request):
        response = PayPalConnector.capture_payment(external_id=request.data["external_id"])

        if response:
            return Response(data = {
                "status": "success",
                "message": "Payment captured successfully"
            }, status=status.HTTP_200_OK)
        else:
            return Response(data = {
                "status": "error",
                "message": "Failed to capture payment"
            }, status=status.HTTP_400_BAD_REQUEST)
    

      

        
