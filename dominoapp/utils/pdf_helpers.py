from fpdf import FPDF
from django.utils.timezone import now
from datetime import datetime, timedelta
import math
import numpy as np

class PDF(FPDF):
    def footer(self):
        # Go to 1.5 cm from bottom
        self.set_y(-15)
        # Select Arial italic 8
        self.set_font('Arial', 'B', 12)
        # Print centered page number
        self.cell(0, 10, 'Page %s' % self.page_no(), 0, 0, 'C')
        self.set_x(156)
        self.cell(50, 10, 'Fecha: %s' % now().strftime('%d/%m/%Y'), 0, 0, 'C')

def Dicc_colores(color):
    colores = {
        'black' : (0,0,0),
        'white' : (255,255,255),
        'blue' : (0,0,255),
        'red' : (255,0,0),
        'green' : (0,255,0),
        'rose' : (234,74,236),
        'margenta' : (200,60,255),
        'gray1' : (220, 220, 220),
        'gray2' : (240, 240, 240),
    }

    return colores[color]

def set_drowcol(hoja, color):
    cr,cg,cb=Dicc_colores(color)
    hoja.set_draw_color(cr,cg,cb)

def set_fillcol(hoja, color):
    cr,cg,cb=Dicc_colores(color)
    hoja.set_fill_color(cr,cg,cb)

def set_textcol(hoja, color):
    cr,cg,cb=Dicc_colores(color)
    hoja.set_text_color(cr,cg,cb)

def tfont_size(hoja, size):
    hoja.set_font_size(size)

def tfont(hoja, estilo, fuente='Arial'):
    hoja.set_font(fuente, style = estilo)

def create_resume_pdf(transaction_data: dict, admin_list:list[str]):
    #Se definen las caracteristicas del PDF
    pdf = PDF(orientation = 'P', format = 'Letter', unit= 'mm') 
     # Define an alias for total number of pages
    pdf.alias_nb_pages()

    # Crea una pagina en blanco para trabajar
    pdf.add_page()
    
    ### Estilo de la Tabla con doble linea
    tfont(pdf,'B')
    width_table = 194
    height_table = 250

    ### Primera tabla
    x_start = 10; y_start = 7.5

    pdf.rect(x_start, y_start, width_table, height_table, style='D')
    
    border = 1
    
    pdf.set_xy(x_start + 57,y_start + 1)
    pdf.cell(80, 8,"Resumen de ingresos Domino Club" , border=border, align='C', fill=0)
    
    tfont(pdf, '')

    ### DEL dia X AL dia Y
    current_x_1 = x_start + 50; current_y = pdf.get_y() + 10
    pdf.set_xy(current_x_1,current_y)
    pdf.cell(10, 8,"Del:" , border=border, align='L', fill=0)
    pdf.cell(30, 8, transaction_data["from_day"], border=border, align='C', fill=0)

    current_x_2 = pdf.get_x() + 10
    pdf.set_xy(current_x_2,current_y)
    pdf.cell(10, 8,"Al:" , border=border, align='L', fill=0)
    pdf.cell(30, 8, transaction_data["to_day"], border=border, align='C', fill=0)
    
    ## Total de Ingresos Registrados
    current_x_1 = x_start + 10; current_y = pdf.get_y() + 16
    pdf.set_xy(current_x_1,current_y)
    pdf.cell(45, 8,"Total de ingresos:" , border=border, align='L', fill=0)
    pdf.cell(20, 8, str(transaction_data["total_rl"]), border=border, align='C', fill=0)

    ## Promedio diario de Ingresos Registrados
    current_x_2 = pdf.get_x() + 20; 
    pdf.set_xy(current_x_2,current_y)
    pdf.cell(65, 8,"Promedio de ingresos diarias:" , border=border, align='L', fill=0)
    pdf.cell(20, 8, str(transaction_data["mean_rl"]), border=border, align='C', fill=0)
    
    ## Total de extraciones Registradas
    current_y = pdf.get_y() + 10
    pdf.set_xy(current_x_1,current_y)
    pdf.cell(45, 8,"Total de extracciones:" , border=border, align='L', fill=0)
    pdf.cell(20, 8, str(transaction_data["total_ext"]), border=border, align='C', fill=0)

    ## Promedio diario de Extraciones Registradas
    pdf.set_xy(current_x_2,current_y)
    pdf.cell(65, 8,"Promedio de extracciones diarias:" , border=border, align='L', fill=0)
    pdf.cell(20, 8, str(transaction_data["mean_ext"]), border=border, align='C', fill=0)

    ## Monto total en ingreso
    current_y = pdf.get_y() + 20
    pdf.set_xy(current_x_1,current_y)
    pdf.cell(50, 8,"Monto total de ingresos:" , border=border, align='L', fill=0)
    pdf.cell(40, 8, f"{transaction_data['total_amount_rl']} CUP", border=border, align='C', fill=0)

    current_y = pdf.get_y() + 10
    pdf.set_xy(current_x_1,current_y)
    pdf.cell(55, 8,"Monto total de extracciones:" , border=border, align='L', fill=0)
    pdf.cell(40, 8, f"{transaction_data['total_amount_ext']} CUP", border=border, align='C', fill=0)

    current_y = pdf.get_y() + 20
    pdf.set_xy(current_x_1,current_y)
    pdf.cell(65, 8,"Monto promedio de ingresos:" , border=border, align='L', fill=0)
    pdf.cell(40, 8, f"{transaction_data['mean_amount_rl']} CUP", border=border, align='C', fill=0)

    current_y = pdf.get_y() + 10
    pdf.set_xy(current_x_1,current_y)
    pdf.cell(65, 8,"Monto promedio de extracciones:" , border=border, align='L', fill=0)
    pdf.cell(40, 8, f"{transaction_data['mean_amount_ext']} CUP", border=border, align='C', fill=0)

    tfont(pdf,'B')
    current_y = pdf.get_y() + 20
    pdf.set_xy(x_start + 60 ,current_y)
    pdf.cell(40, 8,"Balance Total:" , border=border, align='L', fill=0)
    pdf.cell(40, 8, f"{transaction_data['balance_amount']} CUP", border=border, align='C', fill=0)

    tfont(pdf,'B')
    current_y = pdf.get_y() + 10
    pdf.set_xy(x_start + 60 ,current_y)
    pdf.cell(50, 8,"Recaudado en Juegos:" , border=border, align='L', fill=0)
    pdf.cell(40, 8, f"{transaction_data['game_amount']} CUP", border=border, align='C', fill=0)

    current_y = pdf.get_y() + 20
    pdf.set_xy(x_start, current_y)
    pdf.cell(194, 8,"Desglose por Administrador" , border=0, align='C', fill=0)
    current_y = pdf.get_y() + 8
    pdf.set_xy(x_start, current_y)

    pdf.cell(55, 16,"Administrador" , border=border, align='C', fill=0)
    current_x = pdf.get_x()
    pdf.cell(66, 8,"Recargas" , border=border, align='C', fill=0)
    current_y1 = pdf.get_y() + 8
    pdf.set_xy(current_x, current_y1)
    pdf.cell(33, 8,"Transferencias" , border=border, align='C', fill=0)
    pdf.cell(33, 8,"Saldo" , border=border, align='C', fill=0)
    current_x = pdf.get_x()
    pdf.set_xy(current_x, current_y)
    pdf.cell(33, 16,"Extracciones" , border=border, align='C', fill=0)
    pdf.cell(40, 16,"Balance" , border=border, align='C', fill=0)
    current_y = pdf.get_y() + 8
    pdf.set_xy(x_start, current_y)
    tfont(pdf, '')
    color = 'gray2'
    for row in admin_list:
        if color == 'gray2':            
            color = 'gray1'
        else:
            color = 'gray2'
        set_fillcol(pdf,color)
        current_y = pdf.get_y() + 8
        pdf.set_xy(x_start, current_y)
        pdf.cell(55, 8,row , border=border, align='C', fill=1)
        pdf.cell(33, 8,str(transaction_data["admin_resume"][row]['trans_amount_rl']) , border=border, align='C', fill=1)
        pdf.cell(33, 8,str(transaction_data["admin_resume"][row]['saldo_amount_rl']) , border=border, align='C', fill=1)
        pdf.cell(33, 8,str(transaction_data["admin_resume"][row]['total_admin_amount_ext']) , border=border, align='C', fill=1)
        pdf.cell(40, 8,str(transaction_data["admin_resume"][row]['balance']) , border=border, align='C', fill=1)

    ###########################################################
    ## Se crea el grafico de recargas y extracciones diarias
    pdf.add_page()
    x_start = 10; y_start = 7.5

    pdf.rect(x_start, y_start, width_table, height_table, style='D')
        
    height_graph = height_table/2
    width_graph = width_table-20
    start_x_graph = x_start + 10
    start_y_graph = y_start + 10
    pdf.rect(x_start+10, y_start+10, width_graph, height_graph, style='D')
        
    paso = math.ceil(len(transaction_data["graph"]["days"]) / 30)
    i = 0
    j = 0
    count = 0
    vector_reload = np.array(transaction_data["graph"]["reload"])
    vector_extraction = np.array(transaction_data["graph"]["extraction"])
    vector_balance = np.array(transaction_data["graph"]["balance"])
    max_value1 = max(vector_reload)
    max_value2 = max(vector_extraction)
    max_value3 = max(vector_balance)
    max_value = max(max_value1, max_value2, max_value3)
    
    vector_reload = vector_reload / max_value
    vector_extraction = vector_extraction / max_value
    vector_balance = vector_balance / max_value
    
    value_reload = 0
    value_extraction= 0
    value_balance= 0
    width_graph_cell = width_graph* paso / len(transaction_data["graph"]["days"])
    height_graph_cell = height_graph
    
    for day in transaction_data["graph"]["days"]:
        value_reload = vector_reload[count] if count< len(vector_reload) else 0
        value_extraction = vector_extraction[count] if count< len(vector_reload) else 0
        value_balance = vector_balance[count] if count< len(vector_reload) else 0
        if count == i:
            pdf.set_xy(start_x_graph + width_graph_cell*(j),start_y_graph + height_graph - float(value_reload)*(height_graph_cell))
            set_fillcol(pdf,'blue')
            pdf.cell(width_graph_cell, float(value_reload)*(height_graph_cell), f"{''}", border=border, align='C', fill=1)
            pdf.set_xy(start_x_graph + width_graph_cell*(j),start_y_graph + height_graph - float(value_balance)*(height_graph_cell))
            set_fillcol(pdf,'green')
            pdf.cell(width_graph_cell, float(value_balance)*(height_graph_cell), f"{''}", border=border, align='C', fill=1)
            pdf.set_xy(start_x_graph + width_graph_cell*(j),start_y_graph + height_graph - float(value_extraction)*(height_graph_cell))
            set_fillcol(pdf,'red')
            pdf.cell(width_graph_cell, float(value_extraction)*(height_graph_cell), f"{''}", border=border, align='C', fill=1)
            pdf.set_xy(start_x_graph + width_graph_cell*(j),start_y_graph + height_graph + 1)
            set_fillcol(pdf,'gray1')
            pdf.cell(width_graph_cell, 8, f"{transaction_data["graph"]["days"][count]}", border=border, align='C', fill=1)
            i+=paso
            j+=1
            value_reload = 0
            value_extraction= 0
            value_balance= 0
        count += 1 
    j = 0
    height_graph_cell = height_graph/20
    for i in range (0, int(max_value)+int(max_value/20), int(max_value/20)):
        pdf.set_xy(start_x_graph - 10 , start_y_graph - j*(height_graph_cell) + height_graph )
        j += 1
        pdf.cell(9, height_graph_cell, f"{i}", border=border, align='C', fill=1)
    
    pdf.set_xy(start_x_graph , start_y_graph + height_graph + 20 )
    set_fillcol(pdf,'blue')
    pdf.cell(30, 10, f"{'Reload'}", border=border, align='C', fill=1)
    set_fillcol(pdf,'green')
    pdf.cell(30, 10, f"{'Balance'}", border=border, align='C', fill=1)
    set_fillcol(pdf,'red')
    pdf.cell(30, 10, f"{'Extraction'}", border=border, align='C', fill=1)
    ################################################################################      
    
    print("se termino el pdf")
    return pdf.output(dest='S').encode('latin-1')

def create_resume_game_pdf(transaction_data: dict):
    #Se definen las caracteristicas del PDF
    pdf = PDF(orientation = 'P', format = 'Letter', unit= 'mm') 
     # Define an alias for total number of pages
    pdf.alias_nb_pages()

    # Crea una pagina en blanco para trabajar
    pdf.add_page()
    
    ### Estilo de la Tabla con doble linea
    tfont(pdf,'B')
    width_table = 194
    height_table = 250

    ### Primera tabla
    x_start = 10; y_start = 7.5

    pdf.rect(x_start, y_start, width_table, height_table, style='D')
    
    border = 0
    
    pdf.set_xy(x_start + 25,y_start + 1)
    pdf.multi_cell(130, 8, f"Resumen de transacciones del jugador {transaction_data['player_name']} \n alias: {transaction_data['player_alias']}" , border=1, align='C', fill=0)
    
    tfont(pdf, '')

    ### DEL dia X AL dia Y
    current_x_1 = x_start + 30; current_y = pdf.get_y() + 10
    pdf.set_xy(current_x_1,current_y)
    pdf.cell(60, 8,f"Del: {transaction_data['from_day']}" , border=border, align='R', fill=0)

    current_x_2 = pdf.get_x() + 5
    pdf.set_xy(current_x_2,current_y)
    pdf.cell(60, 8,f"Al: {transaction_data['to_day']}" , border=border, align='L', fill=0)
    
    ## Total de Ingresos Registrados
    current_x_1 = x_start + 10; current_y = pdf.get_y() + 16
    pdf.set_xy(current_x_1,current_y)
    pdf.cell(75, 8,f"Total de monedas: {transaction_data['player_coins']} CUP" , border=border, align='L', fill=0)

    ## Total de Ingresos Registrados
    current_x_1 = x_start + 10; current_y = pdf.get_y() + 16
    pdf.set_xy(current_x_1,current_y)
    pdf.cell(65, 8,"Ingresos por juegos ganados:" , border=border, align='L', fill=0)
    pdf.cell(40, 8, f'{transaction_data["total_amount_win"]} CUP', border=border, align='C', fill=0)
    
    ## Total de extraciones Registradas
    current_y = pdf.get_y() + 10
    pdf.set_xy(current_x_1,current_y)
    pdf.cell(65, 8,"Descuento por juegos perdidos:" , border=border, align='L', fill=0)
    pdf.cell(40, 8, f'{transaction_data["total_amount_loss"]} CUP', border=border, align='C', fill=0)

    tfont(pdf,'B')
    current_y = pdf.get_y() + 10
    pdf.set_xy(current_x_1 ,current_y)
    pdf.cell(65, 8,"Balance Total:" , border=border, align='C', fill=0)
    pdf.cell(40, 8, f"{transaction_data['total_balance']} CUP", border=border, align='C', fill=0)

    current_y = pdf.get_y() + 15
    width_border = 2
    width_table_game = 180
    height_table_game = 40

    count = 0
    count_all = 0
    for trans in transaction_data['list_games']:
        pdf.set_line_width(0.5)
        pdf.rect(current_x_1, current_y, width_table_game,height_table_game, style='D')
        pdf.rect(current_x_1 + width_border,current_y + width_border, width_table_game - 2*width_border, height_table_game - 2*width_border)

        tfont(pdf,'B')
        pdf.set_xy(current_x_1 + width_border + 20,current_y + width_border + 1)
        pdf.cell(60, 8,f"Mesa: {trans['game_id']}" , border=border, align='L', fill=0)
        
        tfont(pdf, '')
        pdf.set_xy(current_x_1 + width_border + 83,current_y + width_border + 1)
        pdf.cell(60, 8,f"Datas Jugadas: {trans['totals_games']}" , border=border, align='L', fill=0)

        current_y = pdf.get_y()
        pdf.set_xy(current_x_1 + width_border + 20,current_y + 15)
        pdf.cell(60, 8,f"Ganancias en juego: {trans['amount_win']}" , border=border, align='L', fill=0)

        current_y_1 = pdf.get_y()
        pdf.set_xy(current_x_1 + width_border + 20,current_y_1 + 10)
        pdf.cell(60, 8,f"Pérdidas en juego: {trans['amount_loss']}" , border=border, align='L', fill=0)

        current_x_2 = pdf.get_x()
        pdf.set_xy(current_x_2 + 10,current_y + 20)
        pdf.cell(60, 8,f"Balance en juego: {trans['balance']}" , border=border, align='L', fill=0)

        current_y = current_y_1 + 30
        count += 1
        count_all +=1
        if ((count_all == 3) or (count == 5 and count_all > 3)) and count_all < len(transaction_data['list_games']):
            pdf.add_page()
            pdf.rect(x_start, y_start, width_table, height_table, style='D')
            current_y = y_start + 2
            count = 0

    if transaction_data['traceback'] is not None:
        pdf.add_page()
        pdf.rect(x_start, y_start, width_table, height_table, style='D')
        current_y = y_start + 2
        color = 'gray2'
        
        for trans_element in transaction_data['traceback']:
            if color == 'gray2':            
                color = 'white'
            else:
                color = 'gray2'
            set_fillcol(pdf,color)

            pdf.set_xy(x_start+0.5 ,current_y)
            pdf.multi_cell(width_table-1, 10,f"Jugó en la 'Mesa: {trans_element.game.id if trans_element.game else None}' a las {datetime.strftime((trans_element.time - timedelta(hours=4) ), '%d-%m-%Y %H:%M:%S')} y {'perdio' if trans_element.from_user is not None else 'gano'} una cantidad de {trans_element.amount} monedas{('. Detalles: ' + str(trans_element.descriptions)) if trans_element.descriptions is not None else '.'}" , border=border, align='L', fill=1)

            current_y = pdf.get_y() + 2

            if current_y > 230:
                pdf.add_page()
                pdf.rect(x_start, y_start, width_table, height_table, style='D')
                current_y = y_start + 2

    return pdf.output(dest='S').encode('latin-1')
    