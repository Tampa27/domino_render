from dominoapp.models import DataGame, Player, MoveRegister
import logging
logger = logging.getLogger('django')

def movement_register(data_game:DataGame, player:Player, tile:str, players:list[Player],automatic:False)-> MoveRegister:
    from dominoapp.serializers import CreateMoveRegister
    move_register = CreateMoveRegister(data={
        "data":data_game.id,
        "player_move": player.id,
        "tile_move": tile,
        "players_in_game": [player_item.id for player_item in players],
        "play_automatic": automatic 
    })

    try:
        move_register.is_valid(raise_exception=True)
        return move_register.save()
    except Exception as error:
        logger.critical(f'Ocurrio una excepcion creando el registro en el juego,\n error: {str(error)}')
        return None