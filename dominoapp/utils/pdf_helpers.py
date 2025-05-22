from fpdf import FPDF
from django.utils.timezone import now

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

def create_resume_pdf(transaction_data: dict):
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
    pdf.cell(20, 8, transaction_data["total_rl"], border=border, align='C', fill=0)

    ## Promedio diario de Ingresos Registrados
    current_x_2 = pdf.get_x() + 20; 
    pdf.set_xy(current_x_2,current_y)
    pdf.cell(65, 8,"Promedio de ingresos diarias:" , border=border, align='L', fill=0)
    pdf.cell(20, 8, transaction_data["mean_rl"], border=border, align='C', fill=0)
    
    ## Total de extraciones Registradas
    current_y = pdf.get_y() + 10
    pdf.set_xy(current_x_1,current_y)
    pdf.cell(45, 8,"Total de extracciones:" , border=border, align='L', fill=0)
    pdf.cell(20, 8, transaction_data["total_ext"], border=border, align='C', fill=0)

    ## Promedio diario de Extraciones Registradas
    pdf.set_xy(current_x_2,current_y)
    pdf.cell(65, 8,"Promedio de extracciones diarias:" , border=border, align='L', fill=0)
    pdf.cell(20, 8, transaction_data["mean_ext"], border=border, align='C', fill=0)

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


    return pdf.output(dest='S').encode('latin-1')
        
