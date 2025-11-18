from enum import Enum
import os

class EnumBehavior:
    @staticmethod
    def set_enum(cls):
        setattr(cls, "text", classmethod(EnumBehavior.choices))
        setattr(cls, "choices", classmethod(EnumBehavior.choices))
        setattr(cls, "get", classmethod(EnumBehavior.get))
        setattr(cls, "from_string", classmethod(EnumBehavior.from_string))

        for name, member in cls.__members__.items():
            setattr(member, 'text', member.value[1])
            setattr(member, 'key', member.value[0])

        return cls

    @staticmethod
    def from_string(cls, text):
        for member in cls:
            if member.value[1] == text:
                return member.value[0]
        raise ValueError(f"{text} is not a valid {cls.__name__} value")

    @staticmethod
    def get(cls, value):
        for member in cls:
            if member.value[0] == value:
                return member.value[1]
        raise ValueError(f"{value} is not a valid text for {cls.__name__}")

    @staticmethod
    def choices(cls):
        return [(member.value[0], member.value[1]) for member in cls]

class AdminNotifyEvents(Enum):
    ADMIN_EVENT_NEW_USER = ('new_user', 'New User')
    ADMIN_EVENT_NEW_RELOAD = ('new_reload', 'New Reload')
    ADMIN_EVENT_NEW_EXTRACTION = ('new_extraction', 'New Extraction')
    ADMIN_EVENT_EMAIL_DELETE_PLAYER = ('send_email_delete_player', 'Send Email Delete Player')
    

class GameStatus:
    
    WAITING_PLAYERS = ("wt","waiting_players")
    GAME_RUNNING = ("ru","running")
    GAME_READY = ('ready','ready_to_play')
    DATA_GAME_FINISHED = ('fi','finished')
    GAME_FINISHED = ('fg','game_finished')
    GAME_PAUSED = ('pa','paused')

    status_choices = [
        WAITING_PLAYERS,
        GAME_RUNNING,
        GAME_READY,
        DATA_GAME_FINISHED,
        GAME_FINISHED,
        GAME_PAUSED,
    ]

class GameVariants:
    DOUBLE_6 = ("d6","Double 6")
    DOUBLE_9 = ("d9","Double 9")

    variant_choices = [
        DOUBLE_6,
        DOUBLE_9
    ]
    
class TournamentStatus:
    
    WAITING_PLAYERS = ("wt","waiting_players")
    GAME_READY = ('ready','ready_to_play')
    GAME_RUNNING = ("ru","running")
    GAME_FINISHED = ('tf','finished')
    GAME_PAUSED = ('pa','paused')

    status_choices = [
        WAITING_PLAYERS,
        GAME_READY,
        GAME_RUNNING,        
        GAME_FINISHED,
        GAME_PAUSED,
    ]

class TransactionStatus:
    TRANSACTION_PENDING = ("p", "pending")
    TRANSACTION_IN_PROCESS = ("ip", "in_process")
    TRANSACTION_COMPLETED = ("cp", "completed")
    TRANSACTION_CANCELED = ("cc", "canceled")

    transaction_choices = [
        TRANSACTION_PENDING,
        TRANSACTION_IN_PROCESS,
        TRANSACTION_COMPLETED,
        TRANSACTION_CANCELED
    ]

class PaymentStatus:
    Payment_PENDING = ("pending", "pago pendiente")
    Payment_PAID = ("paid", "pago completado")
    Payment_CANCELED = ("canceled", "pago cancelado")

    payment_choices = [
        Payment_PENDING,
        Payment_PAID,
        Payment_CANCELED
    ]

class TransactionPaymentMethod:
    PAYMENT_BY_SALDO = ("saldo", "saldo movil")
    PAYMENT_BY_TRANSFERENCIA = ("transferencia", "transferencia")
    PAYMENT_BY_PAYPAL = ("paypal", "pago por paypal")
    PAYMENT_BY_ZELLE = ("zelle", "pago por zelle")
    

    payment_choices = [
        PAYMENT_BY_SALDO,
        PAYMENT_BY_TRANSFERENCIA,
        PAYMENT_BY_PAYPAL,
        PAYMENT_BY_ZELLE
    ]

class TransactionTypes:
    TRANSACTION_RELOAD = ("rl", "reload")
    TRANSACTION_EXTRACTION = ("ex", "extraction")
    TRANSATIONS_IN_GAMES = ("gm", "game")
    TRANSACTION_PROMOTION = ("pro", "promotion")
    TRANSACTION_TRANSFER = ("tr", "transfer")

    transaction_type = [
        TRANSACTION_RELOAD, 
        TRANSACTION_EXTRACTION,
        TRANSATIONS_IN_GAMES,
        TRANSACTION_PROMOTION,
        TRANSACTION_TRANSFER
    ]

class ApiConstants:
    DEFAULT_CURRENCY = 'cup'
    DEFAULT_LANGUAGE = 'es'
    EXIT_GAME_TIME = 120        # Tiempo en que si el jugador no hace peticiones a la mesa, se saca automaticamente de ella
    MOVE_TILE_TIME = 20         # Tiempo para que el jugador selecciona la ficha a jugar
    EXIT_TABLE = 40             # Tiempo para sacar al jugado de la mesa si esta inactivo al finalizar un juego
    EXIT_TABLE_2 = 10           # Tiempo para sacar al jugado de la mesa si esta inactivo al finalizar una data
    GAME_FINISH_TIME = 10       # 
    DISCOUNT_PERCENT = 10       # Porciento de descuento en cada transaccion dentro de un juego
    REFER_REWARD = os.environ.get('REFER_REWARD',10) # Monedas ganadas al referido hacer su primera recarga
    INACTIVE_PlAYER_DAYS = 9    
    AUTO_MOVE_WAIT = 3          # Tiempo para que juego el automatico
    AUTO_WAIT_PATNER = 7        # Tiempo que el automatico espera por la entrada de los compañeros antes de comenzar
    AUTO_WAIT_WINNER = 7        # Tiempo que espera el automatico para que decida el ganador quien entre el y su pareja va a salir
    AUTO_PASS_WAIT = 2          # Tiempo del automatico para pasar a un jugador
    AUTO_START_WAIT = 10        # Tiempo que espera el automatico para comenzar un juego
    AUTO_EXIT_GAME = 300        # Tiempo en que el automatico te saca de la mesa por inactividad
    AdminNotifyEvents = EnumBehavior.set_enum(AdminNotifyEvents)
