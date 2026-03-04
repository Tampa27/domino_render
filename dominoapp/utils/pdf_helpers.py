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

    # Montos en USD
    current_x_2 = pdf.get_x() + 20
    pdf.set_xy(current_x_2,current_y)
    pdf.cell(40, 8,"Ingresos en USD:" , border=border, align='L', fill=0)
    pdf.cell(30, 8, f"{transaction_data['total_amount_rl_USD']} USD", border=border, align='C', fill=0)


    current_y = pdf.get_y() + 10
    pdf.set_xy(current_x_1,current_y)
    pdf.cell(55, 8,"Monto total de extracciones:" , border=border, align='L', fill=0)
    pdf.cell(40, 8, f"{transaction_data['total_amount_ext']} CUP", border=border, align='C', fill=0)

    # Cantidades en USD
    pdf.set_xy(current_x_2,current_y)
    pdf.cell(55, 8,"Cantidad Recargas USD:" , border=border, align='L', fill=0)
    pdf.cell(15, 8, f"{transaction_data['total_rl_USD']}", border=border, align='C', fill=0)


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

    resume_by_admin(pdf, x_start, border, admin_list, transaction_data["admin_resume"])

    graph_resume(pdf, width_table, height_table, transaction_data["graph"])
    
    return pdf.output(dest='S').encode('latin-1')

def resume_by_admin(pdf: PDF, x_start, border, admin_list, admin_data):
    # Configuración de columnas
    COL_CONFIG = {
        'admin': (47, 'Administrador'),
        'recargas': [
            (30, 'Transferencia', 'trans_amount_rl'),
            (22, 'Saldo', 'saldo_amount_rl'),
            (15, 'Cant', 'trans_num')
        ],
        'extracciones': [
            (30, 'Monto', 'total_admin_amount_ext'),
            (15, 'Cant', 'ext_num')
        ],
        'balance': (35, 'Balance', 'balance')
    }
       
    # Posición inicial
    y = pdf.get_y() + 20
    pdf.set_xy(x_start, y)
    
    # Título
    pdf.cell(190, 8, "Desglose por Administrador", border=0, align='C', fill=0)
    y += 8
    pdf.set_xy(x_start, y)
    
    # Encabezados principales
    start_x = x_start
    pdf.cell(COL_CONFIG['admin'][0], 16, COL_CONFIG['admin'][1], border, align='C', fill=0)
    
    # Encabezados de Recargas
    x = pdf.get_x()
    pdf.set_xy(x, y)
    pdf.cell(67, 8, "Recargas", border, align='C', fill=0)
    pdf.set_xy(x, y + 8)
    for w, t, _ in COL_CONFIG['recargas']:
        pdf.cell(w, 8, t, border, align='C', fill=0)
    
    # Encabezados de Extracciones
    x = pdf.get_x()
    pdf.set_xy(x, y)
    pdf.cell(45, 8, "Extracciones", border, align='C', fill=0)
    pdf.set_xy(x, y + 8)
    for w, t, _ in COL_CONFIG['extracciones']:
        pdf.cell(w, 8, t, border, align='C', fill=0)
    
    # Balance
    pdf.set_xy(pdf.get_x(), y)
    pdf.cell(COL_CONFIG['balance'][0], 16, COL_CONFIG['balance'][1], border, align='C', fill=0)
    
    # Preparar totales
    totals = {key: 0 for _, cols in [('recargas', COL_CONFIG['recargas']), 
                                     ('extracciones', COL_CONFIG['extracciones'])] 
              for *_, key in cols}
    totals['balance'] = 0
    
    # Dibujar filas de datos
    y += 16
    tfont(pdf, '')
    
    for i, admin in enumerate(admin_list):
        color = 'gray1' if i % 2 else 'gray2'
        set_fillcol(pdf, color)
        pdf.set_xy(x_start, y)
        
        # Administrador
        pdf.cell(COL_CONFIG['admin'][0], 8, admin, border, align='C', fill=1)
        
        # Recargas
        for w, _, key in COL_CONFIG['recargas']:
            val = admin_data[admin][key]
            pdf.cell(w, 8, str(val), border, align='C', fill=1)
            totals[key] += val
        
        # Extracciones
        for w, _, key in COL_CONFIG['extracciones']:
            val = admin_data[admin][key]
            pdf.cell(w, 8, str(val), border, align='C', fill=1)
            totals[key] += val
        
        # Balance
        balance = admin_data[admin]['balance']
        pdf.cell(COL_CONFIG['balance'][0], 8, str(balance), border, align='C', fill=1)
        totals['balance'] += balance
        
        y += 8
    
    # Fila de totales
    set_fillcol(pdf, 'green')
    pdf.set_xy(x_start, y)
    pdf.cell(COL_CONFIG['admin'][0], 8, "TOTALES", border, align='C', fill=1)
    
    for _, cols in [('recargas', COL_CONFIG['recargas']), 
                   ('extracciones', COL_CONFIG['extracciones'])]:
        for w, _, key in cols:
            pdf.cell(w, 8, str(totals[key]), border, align='C', fill=1)
    
    pdf.cell(COL_CONFIG['balance'][0], 8, str(totals['balance']), border, align='C', fill=1)

def graph_resume(pdf: PDF, width_table, height_table, graph_data):
    ###########################################################
    ## Se crea el grafico de lineas de recargas y extracciones diarias
    pdf.add_page()
    x_start = 10
    y_start = 7.5
    
    # Contenedor principal
    pdf.rect(x_start, y_start, width_table, height_table, style='D')
    
    # Área del gráfico
    height_graph = height_table * 0.6  # 60% para el gráfico
    width_graph = width_table - 40  # Margen para etiquetas
    start_x_graph = x_start + 30  # Espacio para etiqueta Y
    start_y_graph = y_start + 15
    
    # Marco del gráfico
    pdf.rect(start_x_graph - 5, start_y_graph - 5, width_graph + 10, height_graph + 10, style='D')
    
    # Preparar datos
    days = graph_data["days"]
    n_days = len(days)
    
    # Convertir a arrays numpy para mejor manejo
    reload_data = np.array(graph_data["reload"], dtype=float)
    extraction_data = np.array(graph_data["extraction"], dtype=float)
    balance_data = np.array(graph_data["balance"], dtype=float)
    
    # Calcular máximo para escalar
    max_value = max(np.max(reload_data), np.max(extraction_data), np.max(balance_data))
    if max_value == 0:
        max_value = 1  # Evitar división por cero
    
    # Escalar datos al alto del gráfico
    reload_scaled = (reload_data / max_value) * height_graph
    extraction_scaled = (extraction_data / max_value) * height_graph
    balance_scaled = (balance_data / max_value) * height_graph
    
    # Calcular posición X para cada punto
    step_x = width_graph / (n_days - 1) if n_days > 1 else width_graph
    
    # Colores para las líneas
    colors = {
        'reload': (0, 0, 255),      # Azul
        'balance': (0, 255, 0),      # Verde
        'extraction': (255, 0, 0)    # Rojo
    }
    
    def draw_line(data_scaled, color, label):
        """Dibuja una línea en el gráfico"""
        nonlocal start_x_graph, start_y_graph, height_graph, step_x
        
        # Configurar color y estilo de línea
        pdf.set_draw_color(color[0], color[1], color[2])
        pdf.set_line_width(1.5)
        
        # Dibujar puntos y líneas
        points = []
        for i, value in enumerate(data_scaled):
            x = start_x_graph + (i * step_x)
            y = start_y_graph + height_graph - value
            points.append((x, y))
            
            # Dibujar punto
            pdf.set_fill_color(color[0], color[1], color[2])
            pdf.ellipse(x - 1.5, y - 1.5, 3, 3, 'F')
        
        # Dibujar líneas entre puntos
        for i in range(len(points) - 1):
            pdf.line(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
    
    def draw_grid():
        """Dibuja la cuadrícula de fondo"""
        pdf.set_draw_color(200, 200, 200)  # Gris claro
        pdf.set_line_width(0.2)
        
        # Líneas horizontales (valores)
        n_horizontal_lines = 5
        for i in range(n_horizontal_lines + 1):
            y = start_y_graph + height_graph - (i * height_graph / n_horizontal_lines)
            pdf.line(start_x_graph - 5, y, start_x_graph + width_graph + 5, y)
        
        # Líneas verticales (días)
        if n_days > 1:
            for i in range(0, n_days, max(1, n_days // 10)):  # Máximo 10 líneas
                x = start_x_graph + (i * step_x)
                pdf.line(x, start_y_graph - 5, x, start_y_graph + height_graph + 5)
    
    def draw_axes():
        """Dibuja los ejes y etiquetas"""
        # Ejes principales
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(1)
        
        # Eje X
        pdf.line(start_x_graph - 5, start_y_graph + height_graph, 
                start_x_graph + width_graph + 5, start_y_graph + height_graph)
        
        # Eje Y
        pdf.line(start_x_graph - 5, start_y_graph - 5, 
                start_x_graph - 5, start_y_graph + height_graph + 5)
    
    def draw_labels():
        """Dibuja las etiquetas de los ejes"""
        pdf.set_font('Arial', '', 8)
        pdf.set_text_color(0, 0, 0)
        
        # Etiquetas del eje X (días)
        label_step = max(1, n_days // 15)  # Mostrar máximo 15 etiquetas
        for i in range(0, n_days, label_step):
            x = start_x_graph + (i * step_x)
            pdf.set_xy(x - 15, start_y_graph + height_graph + 5)
            pdf.cell(30, 8, str(days[i]), border=0, align='C')
        
        # Etiquetas del eje Y (valores)
        n_labels = 5
        for i in range(n_labels + 1):
            value = int((max_value / n_labels) * i)
            y = start_y_graph + height_graph - (i * height_graph / n_labels)
            pdf.set_xy(start_x_graph - 25, y - 4)
            pdf.cell(15, 8, str(value), border=0, align='R')
    
    def draw_legend():
        """Dibuja la leyenda"""
        legend_y = start_y_graph + height_graph + 30
        legend_x = start_x_graph
        
        # Recargas (Azul)
        pdf.set_fill_color(0, 0, 255)
        pdf.rect(legend_x, legend_y, 10, 10, 'F')
        pdf.set_xy(legend_x + 15, legend_y)
        pdf.cell(30, 10, "Recargas", border=0, align='L')
        
        # Balance (Verde)
        pdf.set_fill_color(0, 255, 0)
        pdf.rect(legend_x + 60, legend_y, 10, 10, 'F')
        pdf.set_xy(legend_x + 75, legend_y)
        pdf.cell(30, 10, "Balance", border=0, align='L')
        
        # Extracciones (Rojo)
        pdf.set_fill_color(255, 0, 0)
        pdf.rect(legend_x + 120, legend_y, 10, 10, 'F')
        pdf.set_xy(legend_x + 135, legend_y)
        pdf.cell(30, 10, "Extracciones", border=0, align='L')
    
    def add_title():
        """Añade título al gráfico"""
        pdf.set_font('Arial', 'B', 12)
        pdf.set_xy(x_start + 10, y_start)
        pdf.cell(width_table - 20, 10, "Evolución Diaria de Recargas y Extracciones", 
                border=0, align='C')
    
    # Dibujar todos los elementos
    add_title()
    draw_grid()
    draw_axes()
    
    # Dibujar líneas
    draw_line(reload_scaled, colors['reload'], "Recargas")
    draw_line(balance_scaled, colors['balance'], "Balance")
    draw_line(extraction_scaled, colors['extraction'], "Extracciones")
    
    # Dibujar etiquetas y leyenda
    draw_labels()
    draw_legend()
    
    ################################################################################

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
    