from django.utils.timezone import timedelta, now
from openpyxl import Workbook
from io import BytesIO
import logging  
logger = logging.getLogger('django')

def create_xlsx_file(title: str, players) -> bytes:
    """
    Genera un XLSX con los datos de los jugadores y devuelve los bytes.
    `players` puede ser un iterable de instancias Player
    (queryset.iterator() o una lista).
    """
    if not title:
        raise ValueError('title is required')

    wb = Workbook()
    ws = wb.active
    ws.title = title

    time_in_cuba = now() - timedelta(hours=4)
    ws['A1'] = time_in_cuba.strftime("%d-%m-%Y %H:%M:%S")
    ws['A2'] = 'Alias'
    ws['B2'] = 'Earned Coins'
    ws['C2'] = 'Recharged Coins'
    ws['D2'] = 'Email'
    ws['E2'] = 'Name'
    ws['F2'] = 'Last Time System'

    for index, player in enumerate(players, start=3):
        ws[f'A{index}'] = player.alias
        ws[f'B{index}'] = player.earned_coins
        ws[f'C{index}'] = player.recharged_coins
        ws[f'D{index}'] = player.email
        ws[f'E{index}'] = player.name
        ws[f'F{index}'] = (
            player.lastTimeInSystem.strftime("%d-%m-%Y %H:%M:%S")
            if player.lastTimeInSystem else ""
        )

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()