from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, datetime
from models.recetaxciclo import RecetaXCiclo
from models.ciclo import Ciclo
from models.recetaxciclo import Recetario
from models.torre import Torre

from collections import defaultdict
from datetime import datetime

from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

from io import BytesIO

import logging

logger = logging.getLogger("uvicorn")

def agregarDatosExcel(sheet, producto, ciclos):

    sheet.append(["Nombre: ", producto])
    nombre_cell = sheet.cell(row=sheet.max_row, column=1)
    nombre_cell.font = Font(bold= False, size=16)
    nombre_cell = sheet.cell(row=sheet.max_row, column=2)  
    nombre_cell.font = Font(bold=False, size=16) 

    sheet.append([])

    sheet.append(["LISTA DE CICLOS"])
    ciclos_cell = sheet.cell(row=sheet.max_row, column=1)
    ciclos_cell.font = Font(bold= True, size=12)

    headers = ["IdCiclo", "TagTorre", "FechaInicio", "FechaFin", "TipoFin","CantidadNivelesCorrectos","PesoTorreFila","PesoTorreProducto", "Lote", "TiempoTotal"]
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

    print(f"NOMBRE DE LA TABLA EN BASE NMA PRODUCTO: {producto}")
    tabla_nombre = f"TablaCiclos_{producto.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    tabla = Table(displayName=tabla_nombre, ref=table_range)

    # Aplicar estilo a la tabla
    style = TableStyleInfo(showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=True)
    tabla.tableStyleInfo = style

    # Agregar la tabla a la hoja
    sheet.add_table(tabla)

    # Espacio en blanco al final de cada producto
    sheet.append([])

def buscarCiclosXReceta(idReceta, listaRecetaXCiclo, listaReceta_dic, listaCiclos_dic):
    return [
        [
            recetaXCiclo.id_ciclo,
            listaCiclos_dic[recetaXCiclo.id_ciclo].id_torre,
            listaCiclos_dic[recetaXCiclo.id_ciclo].fecha_inicio,
            listaCiclos_dic[recetaXCiclo.id_ciclo].fecha_fin,
            listaCiclos_dic[recetaXCiclo.id_ciclo].bandaDesmolde,
            recetaXCiclo.cantidadNivelesFinalizado, 
            recetaXCiclo.pesoPorNivel,
            recetaXCiclo.pesoPorNivel * recetaXCiclo.cantidadNivelesFinalizado,
            listaCiclos_dic[recetaXCiclo.id_ciclo].lote, 
            listaCiclos_dic[recetaXCiclo.id_ciclo].tiempoDesmolde
        ]
        for _, recetaXCiclo, _ in listaRecetaXCiclo  # Desempaquetar la tupla correctamente
        if recetaXCiclo.id_recetario == idReceta
    ]

def buscarCiclos(idReceta, listaRecetaXCiclo, listaReceta_dic, listaCiclos_dic):
    return [
        {
            "id_ciclo": recetaXCiclo.id_ciclo,  # Acceder a recetaXCiclo.id_ciclo
            "pesoTotal": listaCiclos_dic[recetaXCiclo.id_ciclo].pesoDesmoldado,
            "tiempoTotal": listaCiclos_dic[recetaXCiclo.id_ciclo].tiempoDesmolde
        }
        for _, recetaXCiclo, _ in listaRecetaXCiclo  # Desempaquetar la tupla correctamente
        if recetaXCiclo.id_recetario == idReceta
    ]

def generarDocumentoXLMS(db, fecha_inicio: date, fecha_fin:date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())
    productosRealizados = {}
    datosParaExcel = []

    tablaCiclo = (
        db.query(Ciclo, RecetaXCiclo, Recetario)
        .join(RecetaXCiclo, Ciclo.id == RecetaXCiclo.id_ciclo)
        .join(Recetario, RecetaXCiclo.id_recetario == Recetario.id)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )

    for ciclo, recetaXCiclo, receta in tablaCiclo:
        if receta.id not in productosRealizados:
            productosRealizados[receta.id] = receta.id
            datosParaExcel.append(
                {
                    "nombre": receta.codigoProducto,
                    "ciclos": buscarCiclosXReceta(receta.id, tablaCiclo, {r.id: r for _,_,r in tablaCiclo}, {c.id: c for c,_,_ in tablaCiclo} )
                }
            )

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reporte Productividad"
    logoPath = "cremona.png"
    img = Image(logoPath)
    img.width = 280
    img.height = 70
    sheet.add_image(img, 'C1')

    sheet.append(["LISTA PRODUCTOS"])
    producto_cell = sheet.cell(row=sheet.max_row, column=1)
    producto_cell.font = Font(bold= True, size=20)

    for producto in datosParaExcel:
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

    excel_stream = BytesIO()
    workbook.save(excel_stream)
    workbook.close() 
    excel_stream.seek(0)  
    return excel_stream


### -------------------------DATOS CONSERVAR ------------------------
def resumenDeProductividad(db, fecha_inicio:date, fecha_fin:date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

    respuestaProductividad = {}
    productosRealizados = {}
    totalPeso = 0
    cantidadCiclosTotal = 0

    tablaCiclos = (
        db.query(Ciclo, RecetaXCiclo, Recetario)
        .join(RecetaXCiclo, Ciclo.id == RecetaXCiclo.id_ciclo)
        .join(Recetario, RecetaXCiclo.id_recetario == Recetario.id)
        .filter(Ciclo.fecha_fin.between(fecha_inicio,fecha_fin))
        .all()
    )

    for ciclo, recetaXCiclo, receta in tablaCiclos:
        totalPeso += ciclo.pesoDesmoldado
        cantidadCiclosTotal += 1
        if receta.id not in productosRealizados:
            listaBuscarCiclo = buscarCiclos(receta.id, tablaCiclos, {r.id: r for _,_, r in tablaCiclos}, {c.id: c for c, _, _ in tablaCiclos})

            pesoFinal = sum(cicloData["pesoTotal"] for cicloData in listaBuscarCiclo)
            tiempoTotalCiclo = sum(cicloData["tiempoTotal"] for cicloData in listaBuscarCiclo)

            productosRealizados[receta.id] = {
                "id_recetario": receta.id,
                "NombreProducto": receta.codigoProducto,
                "pesoTotal": pesoFinal,
                "cantidadCiclos": len(listaBuscarCiclo),
                "tiempoTotal": tiempoTotalCiclo,
            }
    respuestaProductividad["CantidadCiclosCorrectos"] = cantidadCiclosTotal
    respuestaProductividad["PesoTotalCiclos"] = totalPeso / 1000 # Total en Toneladas
    respuestaProductividad["ProductosRealizados"] = list(productosRealizados.values())

    return respuestaProductividad

def generarDocumentoXLMSProductividad(db, fecha_inicio:date, fecha_fin:date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())
    
    tablaBaseDatos = (
        db.query(Ciclo, RecetaXCiclo, Recetario, Torre)
        .join(RecetaXCiclo, Ciclo.id == RecetaXCiclo.id_ciclo)
        .join(Recetario, RecetaXCiclo.id_recetario == Recetario.id)
        .join(Torre, Ciclo.id_torre == Torre.id)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reporte Productividad"
    logoPath = "cremona.png"
    img = Image(logoPath)
    img.width = 280
    img.height = 70
    sheet.add_image(img, 'D1')

    sheet.append(["LISTA PRODUCTOS"])
    producto_cell = sheet.cell(row=sheet.max_row, column=1)
    producto_cell.font = Font(bold= True, size=20)

    sheet.append(["Fecha Inicio:", fecha_inicio.strftime("%Y-%m-%d")])
    fechaInicio_cell = sheet.cell(row=sheet.max_row, column=1)
    fechaInicio_cell.font = Font(bold=True, size=12)
    sheet.append(["Fecha Fin:", fecha_fin.strftime("%Y-%m-%d")])
    fechaFin_cell = sheet.cell(row=sheet.max_row, column=1)
    fechaFin_cell.font = Font(bold=True, size=12)

    headers = ["id_recetario", "CodigoProducto","id_etapa","Cantidad Ciclos","PesoTotalDesmoldado","TiempoTotalDesmoldado","NivelesTorre", "NivelesDesmoldadoCorrectamente"]
    sheet.append(headers)

    header_fill = PatternFill(start_color="145f82", end_color="145f82", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)  

    for col in range(1, len(headers) + 1):
        cell = sheet.cell(row=sheet.max_row, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    start_row = sheet.max_row + 1
    resultado = []
    productosRealizados = {}

    def sumarDatosCiclos(id_recetario, recetaXCiclo, torre_dic, ciclo_dic):
        return [
            [
                ciclo_dic[recetaCiclo.id_ciclo].pesoDesmoldado, 
                ciclo_dic[recetaCiclo.id_ciclo].tiempoDesmolde,
                torre_dic[ciclo_dic[recetaCiclo.id_ciclo].id_torre].cantidadNiveles,
                recetaCiclo.cantidadNivelesFinalizado,
            ] 
            for _, recetaCiclo,_,_ in recetaXCiclo
            if recetaCiclo.id_recetario == id_recetario
        ]
    for ciclo, recetaXCiclo, receta, torre in tablaBaseDatos:
        if receta.id not in productosRealizados:
            productosRealizados[receta.id] = receta.id
            
            resultadoCiclo = sumarDatosCiclos(
                receta.id,
                tablaBaseDatos,
                {r.id: r for _, _, _, r in tablaBaseDatos},
                {c.id: c for c, _, _, _ in tablaBaseDatos}
            )
            
            # Inicializa una fila con los datos básicos
            fila = [
                receta.id,
                receta.codigoProducto,
                ciclo.id_etapa,
                len(resultadoCiclo)  # Cantidad de ciclos
            ]
            
            # Calcula los totales de cada columna adicional
            if resultadoCiclo:
                sumarCiclos = [0] * len(resultadoCiclo[0])
                for vector in resultadoCiclo:
                    #sumarCiclos = [x + y for x, y in zip(sumarCiclos, vector)]
                    sumarCiclos = [x + y for x, y in zip(sumarCiclos, (v if v is not None else 0 for v in vector))]

                fila.extend(sumarCiclos)
            else:
                fila.extend([0, 0, 0, 0])  # Rellena con ceros si no hay datos
            
            # Agrega la fila completa a `resultado`
            resultado.append(fila)
    for receta in resultado:
        if isinstance(receta, (list, tuple)):
            sheet.append(receta)
        else:
            print(f"Fila inválida: {receta}")


    
    end_row = sheet.max_row
    start_col = 1
    end_col = len(headers)
    table_range = f"{sheet.cell(row=start_row -1, column=start_col).coordinate}:{sheet.cell(row=end_row, column=end_col).coordinate}"
    table_nombre = "ReporteProductividad"
    tabla = Table(displayName=table_nombre, ref=table_range)
    style = TableStyleInfo(showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=True)
    tabla.tableStyleInfo = style

    # Agregar la tabla a la hoja
    sheet.add_table(tabla)
    sheet.append([])

    for col in sheet.columns:
        max_length = 0
        column_letter = col[0].column_letter
        for cell in col:
            try:
                max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        sheet.column_dimensions[column_letter].width = max_length + 2

    excel_stream = BytesIO()
    workbook.save(excel_stream)
    workbook.close() 
    excel_stream.seek(0)  
    return excel_stream


def graficosHistoricos(db, fecha_inicio:date, fecha_fin:date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

    resultado = {}
    listaPeso = []
    listaCiclos = []
    listaProductos = {}

    tablaBaseDatos = (
        db.query(Ciclo, RecetaXCiclo, Recetario)
        .join(RecetaXCiclo, Ciclo.id == RecetaXCiclo.id_ciclo)
        .join(Recetario, RecetaXCiclo.id_recetario == Recetario.id)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )
    
    def buscarCiclos(idReceta, tablaDatos):
        return [{
            "idCiclo": ciclo.id,
            "pesoDesmontado": receta.pesoPorNivel * recetaXCiclo.cantidadNivelesFinalizado,
            "fecha_fin" : ciclo.fecha_fin.timestamp(),            
        } for ciclo, recetaXCiclo, receta in tablaDatos if idReceta == recetaXCiclo.id_recetario ]

    for ciclo, recetaXCiclo, receta in tablaBaseDatos:
        listaPeso.append({
            "fecha_fin": ciclo.fecha_fin.strftime("%Y-%m-%d"),
            "PesoDiarioProducto": receta.pesoPorNivel * recetaXCiclo.cantidadNivelesFinalizado
        })
        if recetaXCiclo.id_recetario not in listaProductos:
            listaProductos[recetaXCiclo.id_recetario] = {
                "NombreProducto": receta.codigoProducto,
                "ListaDeCiclos": buscarCiclos(recetaXCiclo.id_recetario, tablaBaseDatos)
            }

    # AGRUPAR POR DIA
    def agruparPorDia(datos):
        grouped_by_day = defaultdict(list)
        
        for item in datos:
            fechaFin = item.fecha_fin
            dia = fechaFin.strftime("%Y-%m-%d")
            grouped_by_day[dia].append(item)
        return dict(grouped_by_day)

    listaXDia = agruparPorDia({c for c,_,_ in tablaBaseDatos})
    for clave, valor in listaXDia.items():
        elemento = {}
        elemento["fecha_fin"]= clave
        elemento["CantidadCiclos"]= len(valor)
        listaCiclos.append(elemento)
    
    listaCiclos = sorted(listaCiclos, key=lambda x: datetime.strptime(x['fecha_fin'], "%Y-%m-%d"))
    
    resultado["ListaCiclosDiario"] = listaCiclos
    resultado["pesoTotalDiario "] = listaPeso
    resultado["listaProductos"] = list(listaProductos.values())

    return resultado

def generarDocumentoXLMSGraficos(db, fecha_inicio:date, fecha_fin:date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

    tabalaDatos = (
        db.query(Ciclo, RecetaXCiclo, Recetario)
        .join(Ciclo, RecetaXCiclo.id_ciclo == Ciclo.id)
        .join(Recetario, RecetaXCiclo.id_recetario == Recetario.id)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )
    resultado = []

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reporte Graficos listaProductos"

    logoPath = "cremona.png"
    img = Image(logoPath)
    img.width = 280
    img.height = 70
    sheet.add_image(img, 'D1')

    sheet.append(["REPORTE: LISTA PRODUCTOS"])
    producto_cell = sheet.cell(row=sheet.max_row, column=1)
    producto_cell.font = Font(bold= True, size=20)

    sheet.append(["Fecha Inicio:", fecha_inicio.strftime("%Y-%m-%d")])
    fechaInicio_cell = sheet.cell(row=sheet.max_row, column=1)
    fechaInicio_cell.font = Font(bold=True, size=12)
    sheet.append(["Fecha Fin:", fecha_fin.strftime("%Y-%m-%d")])
    fechaFin_cell = sheet.cell(row=sheet.max_row, column=1)
    fechaFin_cell.font = Font(bold=True, size=12)

    headers = ["IdRecetario", "Codigo Producto", "Estado Maquina","IdCiclo","BandaDesmolde","NumeroGripper","Lote", "PesoDesmoldado (KG)","Tiempo total desmolde (minutos)","FechaInicio", "FechaFin"]
    sheet.append(headers)

    header_fill = PatternFill(start_color="145f82", end_color="145f82", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)  

    for col in range(1, len(headers) + 1):
        cell = sheet.cell(row=sheet.max_row, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    start_row = sheet.max_row + 1

    for ciclo, recetaXCiclo, receta in tabalaDatos:
        resultado.append([
            recetaXCiclo.id_recetario,
            receta.codigoProducto, 
            ciclo.estadoMaquina,
            ciclo.id, 
            ciclo.bandaDesmolde, 
            receta.nroGripper,
            ciclo.lote,
            ciclo.pesoDesmoldado,
            ciclo.tiempoDesmolde,
            ciclo.fecha_inicio,
            ciclo.fecha_fin, 
        ])

    for receta in resultado:
        sheet.append(receta)

    end_row = sheet.max_row
    start_col = 1
    end_col = len(headers)
    table_range = f"{sheet.cell(row=start_row -1, column=start_col).coordinate}:{sheet.cell(row=end_row, column=end_col).coordinate}"
    table_nombre = "GraficoPoductividad"
    tabla = Table(displayName=table_nombre, ref=table_range)
    style = TableStyleInfo(showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=True)
    tabla.tableStyleInfo = style

    # Agregar la tabla a la hoja
    sheet.add_table(tabla)
    sheet.append([])

    for col in sheet.columns:
        max_length = 0
        column_letter = col[0].column_letter
        for cell in col:
            try:
                max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        sheet.column_dimensions[column_letter].width = max_length + 2

    excel_stream = BytesIO()
    workbook.save(excel_stream)
    workbook.close() 
    excel_stream.seek(0)  
    return excel_stream

# ELIMINAR METODOS 
def obtenerRecetasPorFecha(db, fecha_inicio: date, fecha_fin: date):
    #convertir la fecha a timestamp
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())
    

    tablaBaseDatos = (
        db.query(Ciclo, RecetaXCiclo, Recetario)
        .join(RecetaXCiclo, Ciclo.id == RecetaXCiclo.id_ciclo)
        .join(Recetario, RecetaXCiclo.id_recetario == Recetario.id)
        .filter(Ciclo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )
    def buscarCiclos(idReceta, tablaDatos):
        return [{
            "idCiclo": ciclo.id,
            "pesoDesmontado": ciclo.pesoDesmoldado,
            "fecha_fin" : ciclo.fecha_fin.timestamp(),            
        } for ciclo, recetaXCiclo, receta in tablaDatos if idReceta == recetaXCiclo.id_recetario ]

    listaProductos = {}
    for ciclo, recetaXCiclo, receta in tablaBaseDatos:
        if recetaXCiclo.id_recetario not in listaProductos:
            listaProductos[recetaXCiclo.id_recetario] = {
                "NombreProducto": receta.codigoProducto,
                "ListaDeCiclos": buscarCiclos(recetaXCiclo.id_recetario, tablaBaseDatos)
            }

    #return listaCiclo_dic
    return list(listaProductos.values())

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
            registro["PesoDiarioProducto"] = listaCiclos_dic.get(item.id_ciclo).pesoDesmoldado
            listaPeso.append(registro)

    grouped_by_month = defaultdict(list)
    for item in tablaCiclo:
        print(f"Valor de item.fecha_inicio: {item.fecha_inicio}, Tipo: {type(item.fecha_inicio)}")
        fechaInicio = item.fecha_fin
        
        mes = fechaInicio.strftime("%Y-%m")  # Formato "Año-Mes", por ejemplo "2025-01"
        grouped_by_month[mes].append(item)

    grouped_by_month = dict(grouped_by_month)

    def agruparPorDia(datos):
        grouped_by_day = defaultdict(list)
        
        for item in datos:
            fechaFin = item.fecha_fin
            dia = fechaFin.strftime("%Y-%m-%d")
            grouped_by_day[dia].append(item)
        return dict(grouped_by_day)
    
    def agruparPorHora(datos):
        grouped_by_minute = defaultdict(list)
        
        for item in datos:
            fechaFin = item.fecha_fin
            minuto = fechaFin.strftime("%Y-%m-%d %H")  # Agrupa por año, mes, día, hora y minuto
            grouped_by_minute[minuto].append(item)
        
        return dict(grouped_by_minute)


    listaXDia = agruparPorDia(tablaCiclo)
    grupo = []

    def agruparDats(datos):
        registro = {}
        
        for item in datos:
            fecha = item["fecha_fin"]
            
            # Si la fecha ya está en el diccionario, sumamos el peso
            if fecha in registro:
                registro[fecha]["PesoDiarioProducto"] += item["PesoDiarioProducto"]
            else:
                fecha_sin_hora = fecha
                registro[fecha_sin_hora] = {"fecha_fin": fecha_sin_hora, "PesoDiarioProducto": item["PesoDiarioProducto"]}
    
        
        # Retornar solo los valores, con el formato correcto (sin fechas duplicadas)
        return [{"fecha_fin": fecha, "PesoDiarioProducto": registro[fecha]["PesoDiarioProducto"]} for fecha in registro]


    for clave, valor in listaXDia.items():
        elemento = {}
        elemento["fecha_fin"]= clave
        elemento["CiclosCompletados"]= len(valor)
        grupo.append(elemento)

    completo = {}

    completo["ciclos"] = grupo
    completo["pesoProducto"] = agruparDats(listaPeso) 


    return completo
