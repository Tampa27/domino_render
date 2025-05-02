from rest_framework import status
from rest_framework.response import Response
from dominoapp.models import Player, Bank
from dominoapp.utils.transactions import create_reload_transactions, create_extracted_transactions


class PaymentService:

    @staticmethod
    def process_recharge(request):

        check_player = Player.objects.filter(alias=request.data["alias"]).exists()
        if not check_player:
            return Response(data={'status': 'error', "message":'Player not found'}, status=status.HTTP_404_NOT_FOUND)

        player = Player.objects.get(alias=request.data["alias"])
        player.coins+=request.data["coins"]
        
        try:
            bank = Bank.objects.get(id=1)
        except:
            bank = Bank.objects.create()

        bank.balance+=request.data["coins"]
        bank.buy_coins+=request.data["coins"]
        bank.save()

        create_reload_transactions(to_user=player, amount=request.data["coins"], status="cp")
        
        player.save()
        return Response({'status': 'success', "message":'Balance recharged'}, status=status.HTTP_200_OK)
    
    @staticmethod
    def process_extract(request):

        check_player = Player.objects.filter(alias=request.data["alias"]).exists()
        if not check_player:
            return Response(data={'status': 'error', "message":'Player not found'}, status=status.HTTP_404_NOT_FOUND)

        player = Player.objects.get(alias=request.data["alias"])
        if player.coins < request.data["coins"]:
            return Response(data={'status': 'error', "message":"You don't have enough amount"}, status=status.HTTP_409_CONFLICT)
        
        player.coins -= request.data["coins"]
        
        try:
            bank = Bank.objects.get(id=1)
        except:
            bank = Bank.objects.create()

        bank.balance+=request.data["coins"]
        bank.buy_coins+=request.data["coins"]
        bank.save()

        create_reload_transactions(to_user=player, amount=request.data["coins"], status="cp")
        
        player.save()
        return Response({'status': 'success', "message":'Balance recharged'}, status=status.HTTP_200_OK)