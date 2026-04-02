from dominoapp.serializers import CreateMoveRegister
from dominoapp.models import MoveRegister
import logging
logger = logging.getLogger('django')

def movement_register(game_id: int, player_id: int, tile:str, players_id:list[int],automatic:False)-> MoveRegister:
    move_register = CreateMoveRegister(data={
        "game":game_id,
        "player_move": player_id,
        "tile_move": tile,
        "players_in_game": players_id,
        "play_automatic": automatic 
    })

    try:
        move_register.is_valid(raise_exception=True)
        return move_register.save()
    except Exception as error:
        logger.critical(f'Ocurrio una excepcion creando el registro en el juego,\n error: {str(error)}')
        return None