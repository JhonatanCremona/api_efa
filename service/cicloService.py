from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, datetime
from models.recetaxciclo import RecetaXCiclo
from models.ciclo import Ciclo
from models.recetaxciclo import Recetario

from collections import defaultdict
from datetime import datetime

from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo


import os
from io import BytesIO

# Crear un libro de trabajo
workbook = Workbook()

def agregarDatosExcel(sheet, producto, ciclos):

    sheet.append(["Nombre: ", producto])
    nombre_cell = sheet.cell(row=sheet.max_row, column=1)
    nombre_cell.font = Font(bold= True, size=16)
    nombre_cell = sheet.cell(row=sheet.max_row, column=2)  
    nombre_cell.font = Font(bold=True, size=16) 

    sheet.append([])

    sheet.append(["LISTA DE CICLOS"])
    ciclos_cell = sheet.cell(row=sheet.max_row, column=1)
    ciclos_cell.font = Font(bold= True, size=12)

    headers = ["IdCiclo", "IdTorre", "FechaInicio", "FechaFin", "TipoFin","CantidadNivelesCorrectos","PesoTorreFila","PesoTorreProducto", "Lote", "TiempoTotal"]
    sheet.append(headers)

    header_fill = PatternFill(start_color="0070c0", end_color="0070c0", fill_type="solid") 
    header_font = Font(color="FFFFFF", bold=True)  

    for col in range(1, len(headers) + 1):
        cell = sheet.cell(row=sheet.max_row, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    start_row = sheet.max_row + 1

    # Agregar los datos de ciclos
    for ciclo in ciclos:
        sheet.append(ciclo)

    # Definir el rango de la tabla dinámicamente
    end_row = sheet.max_row
    start_col = 1
    end_col = len(headers)
    table_range = f"{sheet.cell(row=start_row - 1, column=start_col).coordinate}:{sheet.cell(row=end_row, column=end_col).coordinate}"


    table_name = f"TablaCiclos_{producto.replace(' ', '_')}"
    tabla = Table(displayName=table_name, ref=table_range)

    # Aplicar estilo a la tabla
    style = TableStyleInfo(showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=True)
    tabla.tableStyleInfo = style

    # Agregar la tabla a la hoja
    sheet.add_table(tabla)

    # Espacio en blanco al final de cada producto
    sheet.append([])

def generarDocumentoExcel(datos):
    sheet = workbook.active
    sheet.title = "Reporte Productividad"

    logoPath = "cremona.png"

    img = Image(logoPath)

    img.width = 250
    img.height = 70

    sheet.add_image(img, 'C1')

    sheet.append(["LISTA PRODUCTOS"])
    producto_cell = sheet.cell(row=sheet.max_row, column=1)
    producto_cell.font = Font(bold= True, size=20)

    for producto in datos:
        agregarDatosExcel(sheet, producto["nombre"], producto["ciclos"])
    
    for col in sheet.columns:
        max_length = 0
        column_letter = col[0].column_letter
        for cell in col:
            try:
                max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        sheet.column_dimensions[column_letter].width = max_length + 2

    # Guardar el archivo Excel
    workbook.save("productos_ciclos.xlsx")
    print("Archivo Excel generado con éxito.")

    excel_stream = BytesIO()
    workbook.save(excel_stream)
    excel_stream.seek(0)  
    return excel_stream

def descargarDocumentoExcel(db, fecha_inicio: date, fecha_fin:date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

    listaRecetaXCiclo = []
    listaRecetas = []
    datosParaExcel = []
    productosRealizados = {}

    tablaCiclo = (
         db.query(Ciclo)
        .join(RecetaXCiclo, Ciclo.id == RecetaXCiclo.id_ciclo)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )

    for item in tablaCiclo:
        listaRecetaXCiclo.append(
            db.query(RecetaXCiclo).filter(RecetaXCiclo.id_ciclo == item.id).first()
        )

    for item in listaRecetaXCiclo:
        listaRecetas.append(
            db.query(Recetario).filter(Recetario.id == item.id_recetario).first()
        )

    listaReceta_dic = {receta.id: receta for receta in listaRecetas}
    listaCiclos_dic = {ciclo.id: ciclo for ciclo in tablaCiclo}

    for item in listaRecetaXCiclo:
        if item.id_recetario not in productosRealizados:
            datosParaExcel.append({
                "nombre": listaReceta_dic.get(item.id_recetario).nombre,
                "ciclos": buscarCiclosXReceta(item.id_recetario, listaReceta_dic, listaCiclos_dic, listaRecetaXCiclo)
            })
    
    
    return generarDocumentoExcel(datosParaExcel)


def buscarCiclosXReceta(idReceta, listaReceta_dic, listaCiclos_dic, listaRecetaXCiclo):
    return [
        [
            ciclo.id_ciclo,
            listaCiclos_dic[ciclo.id_ciclo].id_torre,
            listaCiclos_dic[ciclo.id_ciclo].fecha_inicio,
            listaCiclos_dic[ciclo.id_ciclo].fecha_fin,
            listaCiclos_dic[ciclo.id_ciclo].tipoFin,
            ciclo.cantidadNivelesCorrectos, 
            listaReceta_dic.get(idReceta).pesoProductoXFila,
            listaReceta_dic.get(idReceta).pesoProductoXFila * ciclo.cantidadNivelesCorrectos,
            listaCiclos_dic[ciclo.id_ciclo].lote, 
            listaCiclos_dic[ciclo.id_ciclo].tiempoTotal
        ]
        for ciclo in listaRecetaXCiclo if ciclo.id_recetario == idReceta
    ]

def resumenDeProductiviada(db, fecha_inicio: date, fecha_fin:date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

    resumen= {}
    listaRecetaXCiclo = []
    listaRecetas = []

    tablaCiclo = (
         db.query(Ciclo)
        .join(RecetaXCiclo, Ciclo.id == RecetaXCiclo.id_ciclo)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )

    for item in tablaCiclo:
        listaRecetaXCiclo.append(
            db.query(RecetaXCiclo).filter(RecetaXCiclo.id_ciclo == item.id).first()
        )

    for item in listaRecetaXCiclo:
        listaRecetas.append(
            db.query(Recetario).filter(Recetario.id == item.id_recetario).first()
        )

    listaReceta_dic = {receta.id: receta for receta in listaRecetas}
    listaCiclos_dic = {ciclo.id: ciclo for ciclo in tablaCiclo}

    productosRealizados = {}
    
    resumen["CantidadCiclosFinalizados"] = len(tablaCiclo)

    def buscarCiclos(idReceta):
        return [
            {
                "id_ciclo": ciclo.id_ciclo,
                "pesoTotal": listaReceta_dic.get(idReceta).pesoProductoXFila * ciclo.cantidadNivelesCorrectos,
                "tiempoTotal": listaCiclos_dic[ciclo.id_ciclo].tiempoTotal
            }
            for ciclo in listaRecetaXCiclo if ciclo.id_recetario == idReceta
        ]

    #GENERAR DESCARGA DOCUMENTO

    datosParaExcel = []

    totalPeso = 0
    for item in listaRecetaXCiclo:
        totalPeso += item.cantidadNivelesCorrectos * listaReceta_dic.get(item.id_recetario).pesoProductoXFila
        if item.id_recetario not in productosRealizados:
            listaBuscarCiclo = buscarCiclos(item.id_recetario)
            
            
            datosParaExcel.append({
                "nombre": listaReceta_dic.get(item.id_recetario).nombre,
                "ciclos": buscarCiclosXReceta(item.id_recetario, listaReceta_dic, listaCiclos_dic, listaRecetaXCiclo)
            })

            pesoFinal = 0
            tiempoTotalCiclo = 0
            for data in listaBuscarCiclo:
                print(data)
                pesoFinal += data["pesoTotal"]
                tiempoTotalCiclo += data["tiempoTotal"]

            productosRealizados[item.id_recetario] = {
                "id_recetario": item.id_recetario,
                "NombreProducto": listaReceta_dic.get(item.id_recetario).nombre,
                "peso": pesoFinal,
                "cantidadCiclos": len(listaBuscarCiclo),
                "tiempoTotal": tiempoTotalCiclo,
            }

    productosRealizados = list(productosRealizados.values())

    #generarDocumentoExcel(datosParaExcel)
    global datos_excel_descarga
    datos_excel_descarga = datosParaExcel

    resumen["PesoTotal"] = totalPeso / 1000 
    resumen["ProductosRealizados"] = productosRealizados
    
    return resumen

def save_datosCiclo(opc_client):
    #Nodo torreActual: id Torre
    #Nodo tipoFin (Nuevo) --> Nodo estado
    #Nodo nivelesDesmolde (Fin)
    #Nodo nivelActual  --> cantidadNivelesFin -> 
    #Nodo Nivel_x_estado -->int 
    #BDD -> ETAPA (DESMOLDEO - ENCAJONADO - PALLET)
    #Validacion 
    

    data = 0
    return data

def save_recetaXCiclo():
    data = 0
    return data


def obtenerRecetasPorFecha(db, fecha_inicio: date, fecha_fin: date):
    #convertir la fecha a timestamp
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())
    

    data = (
        db.query(RecetaXCiclo)
        .join(Ciclo, RecetaXCiclo.id_ciclo == Ciclo.id)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
        )
    listaCiclo= []
    listaReceta = []

    for item in data:
        listaCiclo.append(
            db.query(Ciclo).filter(Ciclo.id == item.id_ciclo).first()
        )
        listaReceta.append(
            db.query(Recetario).filter(Recetario.id == item.id_recetario).first()
        )

    listaReceta_dic = {receta.id: receta for receta in listaReceta}
    listaCiclo_dic = {ciclo.id: ciclo for ciclo in listaCiclo}



    resultado = {}

    def buscarNombreReceta(id_recetario):
        return listaReceta_dic.get(id_recetario).nombre
            
    def buscarCiclos(id_recetario):
        return [
            {
                "id_ciclo": ciclo.id,
                "pesoTotal": listaReceta_dic.get(id_recetario).pesoProductoXFila * ciclo.cantidadNivelesCorrectos,
                "fecha_fin": listaCiclo_dic.get(ciclo.id).fecha_fin.timestamp()
            }
            for ciclo in data if ciclo.id_recetario == id_recetario
        ]
    

    for item in data:
        idReceta = item.id_recetario
        if item.id_recetario not in resultado:
            resultado[idReceta] = {
                "nombre": buscarNombreReceta(idReceta),
                "ciclo": buscarCiclos(idReceta)
            }
    
    #return listaCiclo_dic
    return list(resultado.values())

def obtenerListaCiclosXProductos(db, fecha_inicio: date, fecha_fin: date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

    tablaCiclo = (
        db.query(Ciclo)
        .join(RecetaXCiclo, Ciclo.id == RecetaXCiclo.id_ciclo)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )

    listaRecetaXCiclo = []
    for item in tablaCiclo:
        listaRecetaXCiclo.append(
            db.query(RecetaXCiclo).filter(RecetaXCiclo.id_ciclo == item.id).first()
        )

    listaRecetas = []
    for item in listaRecetaXCiclo:
        listaRecetas.append(
            db.query(Recetario).filter(Recetario.id == item.id_recetario).first()
        )

    listaReceta_dic = {receta.id: receta for receta in listaRecetas}
    listaCiclos_dic = {ciclo.id: ciclo for ciclo in tablaCiclo}

    listaPeso = []

    for item in listaRecetaXCiclo:
        registro = {}
        idReceta = item.id_recetario
        if item.id_recetario not in registro:
            registro["fecha_fin"] = listaCiclos_dic.get(item.id_ciclo).fecha_fin.strftime("%Y-%m-%d")
            registro["PesoTotal"] = listaReceta_dic.get(item.id_recetario).pesoProductoXFila * item.cantidadNivelesCorrectos
            listaPeso.append(registro)

    
    


    grouped_by_month = defaultdict(list)
    for item in tablaCiclo:
        print(f"Valor de item.fecha_inicio: {item.fecha_inicio}, Tipo: {type(item.fecha_inicio)}")
        fechaInicio = item.fecha_fin
        
        mes = fechaInicio.strftime("%Y-%m")  # Formato "Año-Mes", por ejemplo "2025-01"
        grouped_by_month[mes].append(item)

    grouped_by_month = dict(grouped_by_month)

    """
    def getWeek(fecha_str):
    # Si fecha_str ya es un objeto datetime, no hacemos nada
        if isinstance(fecha_str, datetime):
            fecha = fecha_str
        else:
            # Si fecha_str es una cadena, la convertimos a datetime
            fecha = datetime.strptime(fecha_str, "%Y-%m-%dT%H:%M:%S")
    
        return fecha.isocalendar()[1] 
    
    semanas = defaultdict(list)
    for itemData in tablaCiclo:
        fechaFin = itemData.fecha_fin
        semana = getWeek(fechaFin)
        semanas[semana].append(itemData)
    """

    

    def agruparPorDia(datos):
        grouped_by_day = defaultdict(list)
        
        for item in datos:
            fechaFin = item.fecha_fin
            dia = fechaFin.strftime("%Y-%m-%d")
            grouped_by_day[dia].append(item)
        return dict(grouped_by_day)

    listaXDia = agruparPorDia(tablaCiclo)

    grupo=[]

    for clave, valor in listaXDia.items():
        elemento = {}
        elemento["fecha_fin"]= clave
        elemento["CantidadCIclos"]= len(valor)
        grupo.append(elemento)

    completo = {}

    completo["ciclos"] = grupo
    completo["pesoProducto"] = listaPeso 


    return completo


