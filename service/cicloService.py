from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, datetime
from models.recetaxciclo import RecetaXCiclo
from models.ciclo import Ciclo
from models.recetaxciclo import Recetario

from fastapi import HTTPException

from desp import db_dependency

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
            listaReceta_dic.get(idReceta).pesoPorNivel,
            listaReceta_dic.get(idReceta).pesoPorNivel * recetaXCiclo.cantidadNivelesFinalizado,
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
            "pesoTotal": listaReceta_dic.get(idReceta).pesoPorNivel * recetaXCiclo.cantidadNivelesFinalizado,
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
        totalPeso += recetaXCiclo.cantidadNivelesFinalizado * receta.pesoPorNivel
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

    headers = ["IdRecetario", "Codigo Producto", "Estado Maquina","IdCiclo","BandaDesmolde","NumeroGripper","Lote", "PesoDesmoldado (KG)","Tiempo total desmolde (minutos)","FechaInicio", "FechaRegistro"]
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
            ciclo.pesoDesmontado,
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
    table_nombre = "GraficoPRoductividad"
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
        return listaReceta_dic.get(id_recetario).codigoProducto
            
    def buscarCiclos(id_recetario):
        return [
            {
                "id_ciclo": ciclo.id,
                "pesoTotal": listaReceta_dic.get(id_recetario).pesoPorNivel * ciclo.cantidadNivelesFinalizado,
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
            registro["PesoDiarioProducto"] = listaReceta_dic.get(item.id_recetario).pesoPorNivel * item.cantidadNivelesFinalizado
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
    def agruparPorMinuto(datos):
        grouped_by_minute = defaultdict(list)
        
        for item in datos:
            fechaFin = item.fecha_fin
            minuto = fechaFin.strftime("%Y-%m-%d %H:%M")  # Agrupa por año, mes, día, hora y minuto
            grouped_by_minute[minuto].append(item)
        
        return dict(grouped_by_minute)


    listaXDia = agruparPorMinuto(tablaCiclo)

    grupo=[]

    for clave, valor in listaXDia.items():
        elemento = {}
        elemento["fecha_fin"]= clave
        elemento["CantidadCiclos"]= len(valor)
        grupo.append(elemento)

    completo = {}

    completo["ciclos"] = grupo
    completo["pesoProducto"] = listaPeso 


    return completo

def guardarDatosCicloBDD(resultadoResumen, db: db_dependency):
    print("")
    """
    esultadoResumen = resumenEtapaDesmoldeo(opc_client)
            estado_actual = resultadoResumen["Estado"]

            # Solo actuamos si el estado cambia
            if estado_actual != ultimo_estado:
                if estado_actual == "Activo":

                    db_ciclo = Ciclo(
                        fecha_inicio=datetime.now(),
                        fecha_fin=datetime.now(),
                        estadoMaquina=resultadoResumen["Estado"],
                        bandaDesmolde=resultadoResumen["BandaDesmolde"], 
                        lote="001",
                        tiempoDesmolde=1,
                        id_etapa=1,
                        id_torre=resultadoResumen["torreActual"],
                    )

                    # Obtener la sesión de la base de datos
                    db_session: Session = db.get_db().__next__()

                    try:
                        # Intentar guardar el ciclo en la base de datos
                        db_session.add(db_ciclo)
                        db_session.commit()  # Confirmar la transacción
                        db_session.refresh(db_ciclo)  # Obtener el id generado
                        logger.info(f"Ciclo guardado con ID: {db_ciclo.id}")
                        ciclo_guardado = db_ciclo  # Guardar la referencia al ciclo creado
                    except Exception as e:
                        db_session.rollback()  # Revertir si ocurre un error
                        logger.error(f"Error al guardar el ciclo: {e}")
                        raise HTTPException(status_code=500, detail=f"Error al guardar el ciclo: {e}")
                    finally:
                        db_session.close()  # Cerrar la sesión de la base de datos

                    # Verificamos si ciclo_guardado no es None después de la transacción
                    if ciclo_guardado is None:
                        logger.error("No se pudo guardar el ciclo correctamente.")
                        raise HTTPException(status_code=500, detail="Error al guardar el ciclo: ciclo_guardado es None.")

                    # Log de confirmación
                    logger.info(f"Ciclo guardado: {ciclo_guardado.id}")

                elif resultadoResumen["NivelActual"] == 2:
                    # Verificamos si ciclo_guardado no es None antes de intentar actualizarlo
                    print("ENTRE AL IF -AAAAAAAAAAAA")
                    if ciclo_guardado is not None:
                        try:
                            logger.info("Actualizando datos del ciclo...")

                            # Actualizamos la fecha de fin para el ciclo guardado
                            ciclo_guardado.fecha_fin = datetime.now()

                            # Obtener la sesión de la base de datos
                            db_session: Session = db.get_db().__next__()

                            # Confirmar la transacción de actualización
                            db_session.commit()
                            db_session.refresh(ciclo_guardado)
                            print("ACTUALICE EL DATO Y LLEGUEEE")
                            logger.info(f"Ciclo actualizado con ID: {ciclo_guardado.id}")
                        except Exception as e:
                            logger.error(f"Error al actualizar el ciclo: {e}")
                            db_session.rollback()  # En caso de error, revertir
                            raise HTTPException(status_code=500, detail=f"Error al actualizar el ciclo: {e}")
                        finally:
                            db_session.close()

                    else:
                        logger.error("No se puede actualizar el ciclo: ciclo_guardado es None.")
                        raise HTTPException(status_code=500, detail="No se ha guardado un ciclo previamente.")

                # Actualizamos el último estado
                ultimo_estado = estado_actual
                
    """
def actualizarDatosCicloActual(ciclo: Ciclo, resultadoResumen, db):
    try:
        ciclo.fecha_fin = datetime.now().strftime("%Y-%m-%d-%H-%M") 
        db.commit()
        db.refresh(ciclo) 

        logger.info(f"Ciclo actualizado con ID: {ciclo.id}")
    except Exception as e:
        # Si ocurre un error, haz rollback
        logger.error(f"Error en el lector central del OPC: {e}")
        