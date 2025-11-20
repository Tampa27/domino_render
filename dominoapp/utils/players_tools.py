import hashlib
from decimal import Decimal
from dominoapp.models import Player

def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
def get_device_hash(request):
    ip_address = get_client_ip(request)    
    print('ip: ', ip_address)
        
    if not ip_address:
        return None
    
    # Concatenate the values and create a SHA-256 hash
    texto = f"{ip_address}"
    hash_sha256 = hashlib.sha256(texto.encode()).hexdigest()
    
    return hash_sha256

def win_expectation_player1_vs_player2(R_player_1: Decimal, R_player_2: Decimal)->Decimal:
     """Calcula la expectativa de victoria del jugador 1 contra el jugador 2 usando la fórmula Elo."""
     E_p1_vs_p2 =1/(1 + 10**((R_player_1 - R_player_2)/400))
     return E_p1_vs_p2

def rate_change(E_player: Decimal, S_player: int, K_player: int)->Decimal:
    """Calcula el cambio en la calificación Elo de un jugador."""
    Delta_R = K_player * (S_player - E_player)
    return Delta_R     

def update_elo(players: list[Player], winner: Player)->None:
    """Actualiza las calificaciones Elo de los jugadores después de un juego."""

    for player in players:
        for opponent in players:
            if player.id != opponent.id:
                E_player1_vs_player2 = win_expectation_player1_vs_player2(player.elo, opponent.elo)
                delta_R_player1 = rate_change(E_player1_vs_player2, 1 if player.id == winner.id else 0, player.elo_factor)
                player.elo += delta_R_player1
                player.save(update_fields=['elo'])
    

def update_elo_pair(pair1: list[Player], pair2: list[Player])->None:
    """
    Actualiza las calificaciones Elo de los jugadores después de un juego entre dos parejas. 
    Se asume que el pair1 siempre es el ganador.
    """
    average_elo_pair1 = sum(player.elo for player in pair1)/2
    average_elo_pair2 = sum(player.elo for player in pair2)/2

    k_factor_pair1 = sum(player.elo_factor for player in pair1)/2
    k_factor_pair2 = sum(player.elo_factor for player in pair2)/2

    E_pair1_vs_pair2 = win_expectation_player1_vs_player2(Decimal(average_elo_pair1), Decimal(average_elo_pair2))
    E_pair2_vs_pair1 = win_expectation_player1_vs_player2(Decimal(average_elo_pair2), Decimal(average_elo_pair1))

    total_delta_R_pair1 = rate_change(E_pair1_vs_pair2, 1, int(k_factor_pair1))
    total_delta_R_pair2 = rate_change(E_pair2_vs_pair1, 0, int(k_factor_pair2))
    
    for player in pair1:
        delta_R_player = total_delta_R_pair1 / 2
        player.elo += delta_R_player
        player.save(update_fields=['elo'])
    for player in pair2:
        delta_R_player = total_delta_R_pair2 / 2
        player.elo += delta_R_player
        player.save(update_fields=['elo'])