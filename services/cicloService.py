import os
from datetime import date, datetime
from collections import defaultdict

from models.cicloDesmoldeo import CicloDesmoldeo
from models.recetario import Recetario
from models.recetarioXCiclo import RecetarioXCiclo
from models.torre import Torre

from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from io import BytesIO


    
def buscarCiclos(id_receta, tabla_datos):
    return [{
        "idCiclo": ciclo.id,
        "pesoDesmontado": ciclo.pesoDesmoldado,
        "fecha_fin": ciclo.fecha_fin.timestamp(),
    } for ciclo, recetaXCiclo, receta in tabla_datos if id_receta == recetaXCiclo.id_recetario]

def buscarCiclos1(idReceta, listaRecetaXCiclo, listaReceta_dic, listaCiclos_dic):
    return [
        {
            "id_ciclo": recetaXCiclo.id_ciclo_desmoldeo,  # Acceder a recetaXCiclo.id_ciclo_desmoldeo
            "pesoTotal": listaCiclos_dic[recetaXCiclo.id_ciclo_desmoldeo].pesoDesmoldado,
            "tiempoTotal": listaCiclos_dic[recetaXCiclo.id_ciclo_desmoldeo].tiempoDesmolde
        }
        for _, recetaXCiclo, _ in listaRecetaXCiclo  # Desempaquetar la tupla correctamente
        if recetaXCiclo.id_recetario == idReceta
    ]

def resumenDeProductividad(db, fecha_inicio:date, fecha_fin:date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

    respuestaProductividad = {}
    productosRealizados = {}
    totalPeso = 0
    cantidadCiclosTotal = 0

    tablaCiclos = (
        db.query(CicloDesmoldeo, RecetarioXCiclo, Recetario)
        .join(RecetarioXCiclo, CicloDesmoldeo.id == RecetarioXCiclo.id_ciclo_desmoldeo)
        .join(Recetario, RecetarioXCiclo.id_recetario == Recetario.id)
        .filter(CicloDesmoldeo.fecha_fin.between(fecha_inicio,fecha_fin))
        .all()
    )

    for ciclo, recetaXCiclo, receta in tablaCiclos:
        totalPeso += ciclo.pesoDesmoldado
        cantidadCiclosTotal += 1
        if receta.id not in productosRealizados:
            listaBuscarCiclo = buscarCiclos1(receta.id, tablaCiclos, {r.id: r for _,_, r in tablaCiclos}, {c.id: c for c, _, _ in tablaCiclos})

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
        db.query(CicloDesmoldeo, RecetarioXCiclo, Recetario, Torre)
        .join(RecetarioXCiclo, CicloDesmoldeo.id == RecetarioXCiclo.id_ciclo_desmoldeo)
        .join(Recetario, RecetarioXCiclo.id_recetario == Recetario.id)
        .outerjoin(Torre, CicloDesmoldeo.id_torre == Torre.id)  # Cambiado a outerjoin para incluir todos los ciclos
        .filter(CicloDesmoldeo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )
    workbook = Workbook()
    
    # PRIMERA HOJA - Reporte Productividad
    sheet = workbook.active
    sheet.title = "Reporte Productividad"
    
    try:
        logoPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "cremona.png")
        img = Image(logoPath)
        img.width = 210
        img.height = 52
        sheet.add_image(img, 'D1')
    except Exception as e:
        print(f"Error al cargar la imagen: {e}")
        # Continuar sin la imagen

    sheet.append(["LISTA PRODUCTOS"])
    producto_cell = sheet.cell(row=sheet.max_row, column=1)
    producto_cell.font = Font(bold= True, size=20)

    sheet.append(["Fecha Inicio:", fecha_inicio.strftime("%Y-%m-%d")])
    fechaInicio_cell = sheet.cell(row=sheet.max_row, column=1)
    fechaInicio_cell.font = Font(bold=True, size=12)
    sheet.append(["Fecha Fin:", fecha_fin.strftime("%Y-%m-%d")])
    fechaFin_cell = sheet.cell(row=sheet.max_row, column=1)
    fechaFin_cell.font = Font(bold=True, size=12)

    # Nuevos headers con solo 5 columnas
    headers = ["Producto", "Cantidad Ciclos", "Peso Total Desmoldado", "Tiempo Total Desmoldado", "Niveles Desmoldados"]
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
    
    # Crear diccionarios para acceso rápido - El problema está en esta línea
    ciclo_dic = {ciclo.id: ciclo for ciclo, _, _, _ in tablaBaseDatos}
    # Filtrar los valores None antes de intentar acceder a torre.id
    torre_dic = {torre.id: torre for _, _, _, torre in tablaBaseDatos if torre is not None}
    receta_dic = {receta.id: receta for _, _, receta, _ in tablaBaseDatos}
    
    # Procesar cada receta única
    recetas_procesadas = set()
    
    for _, recetaXCiclo, receta, _ in tablaBaseDatos:
        if receta.id not in recetas_procesadas:
            recetas_procesadas.add(receta.id)
            
            # Obtener datos agrupados por receta usando la función sumarDatosCiclos
            datos_receta = sumarDatosCiclos(receta.id, tablaBaseDatos, torre_dic, ciclo_dic)
            
            if datos_receta:
                # Calcular totales
                peso_total = sum(item[0] for item in datos_receta)
                tiempo_total = sum(item[1] for item in datos_receta)
                niveles_desmoldados = sum(item[3] for item in datos_receta)
                
                # Agregar a la lista de resultados - solo con las 5 columnas solicitadas
                resultado.append([
                    receta.codigoProducto,
                    len(datos_receta),  # Cantidad de ciclos
                    peso_total,
                    tiempo_total,
                    niveles_desmoldados
                ])
    
    # Agregar datos al Excel
    for fila in resultado:
        sheet.append(fila)
    
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
    
    # Ajustar ancho de columnas en la primera hoja
    for col in sheet.columns:
        max_length = 0
        column_letter = col[0].column_letter
        for cell in col:
            try:
                max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        sheet.column_dimensions[column_letter].width = max_length + 2

    # SEGUNDA HOJA - Reporte por Torre
    sheet_torre = workbook.create_sheet(title="Reporte por Torre")
    
    try:
        logoPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "cremona.png")
        img = Image(logoPath)
        img.width = 210
        img.height = 52
        sheet_torre.add_image(img, 'K1')
    except Exception as e:
        print(f"Error al cargar la imagen en la segunda hoja: {e}")
    
    sheet_torre.append(["REPORTE POR TORRE"])
    titulo_cell = sheet_torre.cell(row=sheet_torre.max_row, column=1)
    titulo_cell.font = Font(bold=True, size=20)
    
    sheet_torre.append(["Fecha Inicio:", fecha_inicio.strftime("%Y-%m-%d")])
    fechaInicio_cell = sheet_torre.cell(row=sheet_torre.max_row, column=1)
    fechaInicio_cell.font = Font(bold=True, size=12)
    sheet_torre.append(["Fecha Fin:", fecha_fin.strftime("%Y-%m-%d")])
    fechaFin_cell = sheet_torre.cell(row=sheet_torre.max_row, column=1)
    fechaFin_cell.font = Font(bold=True, size=12)
    
    # Headers para la hoja de torre
    headers_torre = [
        "N°Lote", "Producto", "Torre", "Niveles Seleccionados", 
        "Niveles Desmoldados", "Peso Desmoldado", "Tipo de Fin", 
        "Cinta de Desmolde", "Inicio", "Fin", "Tiempo Pausado", 
        "Tiempo Total del Ciclo"
    ]
    
    sheet_torre.append(headers_torre)
    
    # Aplicar formato a los headers
    for col in range(1, len(headers_torre) + 1):
        cell = sheet_torre.cell(row=sheet_torre.max_row, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    start_row_torre = sheet_torre.max_row + 1
    resultado_torre = []
    
    # Función para calcular el ID de torre según la fórmula en el SQL
    # IMPORTANTE: Debe definirse ANTES de usarse
    def calcular_torre(id_torre, id_recetario):
        offset_map = {
            1: 0,
            2: 13,
            3: 33,
            4: 37,
            5: 67,
            6: 97,
            7: 101,
            8: 103
        }
        offset = offset_map.get(id_recetario, 0)
        return id_torre + offset
    
    # IMPORTANTE: Consulta separada para la hoja de torres que incluya TODOS los ciclos
    tablaBaseDatosTorre = (
        db.query(CicloDesmoldeo, RecetarioXCiclo, Recetario)
        .join(RecetarioXCiclo, CicloDesmoldeo.id == RecetarioXCiclo.id_ciclo_desmoldeo)
        .join(Recetario, RecetarioXCiclo.id_recetario == Recetario.id)
        .filter(CicloDesmoldeo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )
    
    # Crea un mapeo de productos a tipos de torre
    producto_a_receta = {
        "OVALADO A OVA": 4,  # Para torres OVA
        "OVALADO B OVB": 5,  # Para torres OVB
        "RECTANGULAR 7K": 2,  # Para torres 7K
        "CUADRADO CU": 1,    # Para torres CU
        "MANDOLINA 6K": 3,   # Para torres 6K
        "LUNCH LU": 6,        # Para torres LU
        "CUADRADO LARGO CUA": 7,   # Para torres CUA
        "QUESO PUERCO QP": 8     # Para torres QP
    }
    
    # Cargar todas las torres una sola vez
    torres = db.query(Torre).all()
    torre_map = {torre.NTorre: torre.ActualizarTAG for torre in torres if torre.ActualizarTAG}
    
    tipo_torre_por_rango = {
        (1, 13): "CU",       # Torres 1-13 son CU
        (14, 36): "7K",      # Torres 14-36 son 7K
        (33, 36): "6K",      # Torres 33-36 son 6K
        (37, 66): "OVA",     # Torres 37-66 son OVA
        (67, 96): "OVB",     # Torres 67-96 son OVB
        (97, 100): "LU",     # Torres 97-100 son LU
        (101, 102): "CUA",   # Torres 101-102 son CUA
        (103, 120): "QP"     # Torres 103+ son QP
    }

    # Procesar cada ciclo sin filtro por duración
    ciclos_procesados = set()
    resultado_torre = []

    for ciclo, recetaXCiclo, receta in tablaBaseDatosTorre:
        if ciclo.id in ciclos_procesados:
            continue
        ciclos_procesados.add(ciclo.id)

        try:
            # Determinar el tipo de producto por su nombre
            tipo_producto = None
            for prefijo, id_receta in producto_a_receta.items():
                if receta.codigoProducto.startswith(prefijo):
                    tipo_producto = id_receta
                    break
            
            # Si no se encontró un tipo específico, usar el id_recetario de la base de datos
            if tipo_producto is None:
                tipo_producto = recetaXCiclo.id_recetario
            
            # Calcular torre usando la fórmula proporcionada con el tipo correcto
            torre_calculada = calcular_torre(ciclo.id_torre, tipo_producto)
            
            # Verificar que el tipo de torre coincida con el tipo de producto
            tipo_torre = None
            for (inicio, fin), codigo in tipo_torre_por_rango.items():
                if inicio <= torre_calculada <= fin:
                    tipo_torre = codigo
                    break
            
            # Si el producto es OVALADO A OV, debe usar torres OVA
            if receta.codigoProducto.startswith("OVALADO A OV") and tipo_torre != "OVA":
                print(f"Advertencia: Producto {receta.codigoProducto} usando torre incorrecta {tipo_torre}")
                # Forzar uso de torres OVA
                torre_calculada = 37 + (ciclo.id_torre % 30)  # Asegurar que esté en el rango OVA
                
            # Si el producto es OVALADO B OV, debe usar torres OVB  
            elif receta.codigoProducto.startswith("OVALADO B OV") and tipo_torre != "OVB":
                print(f"Advertencia: Producto {receta.codigoProducto} usando torre incorrecta {tipo_torre}")
                # Forzar uso de torres OVB
                torre_calculada = 67 + (ciclo.id_torre % 30)  # Asegurar que esté en el rango OVB
            
            # Obtener el código de torre
            codigo_torre = torre_map.get(torre_calculada, str(torre_calculada))
            
            # Calcular tiempo total del ciclo
            tiempo_total = round((ciclo.fecha_fin - ciclo.fecha_inicio).total_seconds() / 60, 2)
            tiempo_formateado = f"{tiempo_total} minutos"
            
            # Agregar fila al resultado
            resultado_torre.append([
                ciclo.id,  # N°Lote
                receta.codigoProducto,  # Producto
                codigo_torre,  # Torre con el código correcto
                0,  # Niveles Seleccionados (fijo)
                recetaXCiclo.cantidadNivelesFinalizado,  # Niveles Desmoldados
                ciclo.pesoDesmoldado,  # Peso Desmoldado
                0,  # Tipo de Fin (fijo)
                ciclo.bandaDesmolde,  # Cinta de Desmolde
                ciclo.fecha_inicio,  # Inicio
                ciclo.fecha_fin,  # Fin
                0,  # Tiempo Pausado (fijo)
                tiempo_formateado  # Tiempo Total del Ciclo correctamente formateado
            ])
        except Exception as e:
            print(f"Error procesando ciclo {ciclo.id} para reporte por torre: {e}")

    # Agregar datos a la hoja
    for fila in resultado_torre:
        sheet_torre.append(fila)
    
    # Crear tabla en la segunda hoja
    end_row_torre = sheet_torre.max_row
    tabla_range_torre = f"{sheet_torre.cell(row=start_row_torre - 1, column=1).coordinate}:{sheet_torre.cell(row=end_row_torre, column=len(headers_torre)).coordinate}"
    tabla_torre = Table(displayName="ReportePorTorre", ref=tabla_range_torre)
    tabla_torre.tableStyleInfo = style
    sheet_torre.add_table(tabla_torre)
    
    # Ajustar ancho de columnas en la segunda hoja
    for col in sheet_torre.columns:
        max_length = 0
        column_letter = col[0].column_letter
        for cell in col:
            try:
                max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        sheet_torre.column_dimensions[column_letter].width = max_length + 2
    
    excel_stream = BytesIO()
    workbook.save(excel_stream)
    workbook.close() 
    excel_stream.seek(0)  
    return excel_stream

def sumarDatosCiclos(id_recetario, datos_tabla, torre_dic=None, ciclo_dic=None):
    """
    Función para sumar y agrupar datos de ciclos por recetario.
    
    Args:
        id_recetario: ID del recetario a filtrar
        datos_tabla: Lista de tuplas (CicloDesmoldeo, RecetarioXCiclo, Recetario, [Torre]) de la base de datos
        torre_dic: Diccionario de torres {id: objeto_torre}
        ciclo_dic: Diccionario de ciclos {id: objeto_ciclo}
    
    Returns:
        List de listas con [pesoDesmoldado, tiempoDesmolde, cantidadNiveles, cantidadNivelesFinalizado]
    """
    resultados = []
    ciclos_procesados = set()  # Conjunto para controlar ciclos ya procesados
    
    if torre_dic is None:
        torre_dic = {}
    
    if ciclo_dic is None:
        ciclo_dic = {}
        
    # Para el caso de 4 elementos (CicloDesmoldeo, RecetarioXCiclo, Recetario, Torre)
    if datos_tabla and len(datos_tabla[0]) == 4:
        for ciclo, receta_ciclo, receta, torre in datos_tabla:
            # Solo procesar cada ciclo una vez para este recetario
            if receta_ciclo.id_recetario == id_recetario and ciclo.id not in ciclos_procesados:
                ciclos_procesados.add(ciclo.id)  # Marcar este ciclo como procesado
                try:
                    resultados.append([
                        ciclo.pesoDesmoldado if ciclo else 0,
                        ciclo.tiempoDesmolde if ciclo and hasattr(ciclo, 'tiempoDesmolde') else 0,
                        torre.cantidadNiveles if torre and hasattr(torre, 'cantidadNiveles') else 0,
                        receta_ciclo.cantidadNivelesFinalizado if hasattr(receta_ciclo, 'cantidadNivelesFinalizado') else 0
                    ])
                except Exception as e:
                    print(f"Error procesando ciclo {receta_ciclo.id_ciclo_desmoldeo}: {str(e)}")
                    resultados.append([0, 0, 0, 0])
    
    # El resto de la función debe implementarse similarmente con el set de ciclos_procesados
    elif datos_tabla and len(datos_tabla[0]) == 3:
        for ciclo, receta_ciclo, receta in datos_tabla:
            if receta_ciclo.id_recetario == id_recetario and ciclo.id not in ciclos_procesados:
                ciclos_procesados.add(ciclo.id)  # Marcar este ciclo como procesado
                try:
                    torre_id = ciclo.id_torre if hasattr(ciclo, 'id_torre') else None
                    torre_niveles = torre_dic.get(torre_id, 0)
                    if isinstance(torre_niveles, Torre):
                        torre_niveles = torre_niveles.cantidadNiveles
                    
                    resultados.append([
                        ciclo.pesoDesmoldado if ciclo else 0,
                        ciclo.tiempoDesmolde if ciclo else 0,
                        torre_niveles,
                        receta_ciclo.cantidadNivelesFinalizado
                    ])
                except Exception as e:
                    print(f"Error procesando ciclo {receta_ciclo.id_ciclo_desmoldeo}: {str(e)}")
                    resultados.append([0, 0, 0, 0])
                    
    return resultados
    
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

def get_lista_productos(db, fecha_inicio: date, fecha_fin: date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

    listaProductos = {}
    tablaBDD = (
        db.query(CicloDesmoldeo, RecetarioXCiclo, Recetario)
        .join(RecetarioXCiclo, CicloDesmoldeo.id == RecetarioXCiclo.id_ciclo_desmoldeo)
        .join(Recetario, RecetarioXCiclo.id_recetario == Recetario.id)
        .filter(CicloDesmoldeo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )
    for ciclo, recetaXCiclo, receta in tablaBDD:
        if recetaXCiclo.id_recetario not in listaProductos:
            listaProductos[recetaXCiclo.id_recetario] = {
                "id_recetario": receta.id,
                "NombreProducto": receta.codigoProducto,
                "ListaDeCiclos": buscarCiclos(recetaXCiclo.id_recetario, tablaBDD)
            }
    return list(listaProductos.values())

def generarDocumentoXLMSGraficos(db, fecha_inicio:date, fecha_fin:date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

    tabalaDatos = (
        db.query(CicloDesmoldeo, RecetarioXCiclo, Recetario, Torre)
        .join(RecetarioXCiclo, CicloDesmoldeo.id == RecetarioXCiclo.id_ciclo_desmoldeo)
        .join(Recetario, RecetarioXCiclo.id_recetario == Recetario.id)
        .outerjoin(Torre, CicloDesmoldeo.id_torre == Torre.id)
        .filter(CicloDesmoldeo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )
    
    # Diccionario para agregar datos por producto y día
    datos_agregados = {}
    
    # Mapeo de prefijos de productos a sus códigos cortos
    prefijos_productos = {
        "OVALADO A OV": "(OV-A)",
        "OVALADO B OV": "(OV-B)",
        "RECTANGULAR 7K": "(7K)",
        "CUADRADO CU": "(CU)",
        "MANDOLINA 6K": "(6K)",
        "LUNCH LU": "(LU)",
        "CUADRADO LARGO CUA": "(CUA)",
        "QUESO PUERCO QP": "(QP)"
    }

    # Agrupar y sumar datos por producto y fecha
    for ciclo, recetaXCiclo, receta, _ in tabalaDatos:
        try:
            # Extraer solo la fecha (sin hora)
            fecha_str = ciclo.fecha_fin.strftime("%d/%m/%Y")
            
            # Determinar prefijo del producto para el formato solicitado
            prefijo = ""
            for clave, valor in prefijos_productos.items():
                if receta.codigoProducto.startswith(clave):
                    prefijo = valor
                    break
            
            # Formato del nombre del producto con prefijo
            nombre_producto = f"{prefijo} {receta.codigoProducto}"
            
            # Clave para agrupar (producto, fecha)
            clave = (nombre_producto, fecha_str)
            
            # Si la clave ya existe, sumar valores
            if clave in datos_agregados:
                datos_agregados[clave]['peso'] += ciclo.pesoDesmoldado
                datos_agregados[clave]['tiempo'] += ciclo.tiempoDesmolde
            else:
                # Si es nueva, crear entrada
                datos_agregados[clave] = {
                    'peso': ciclo.pesoDesmoldado,
                    'tiempo': ciclo.tiempoDesmolde
                }
        except Exception as e:
            print(f"Error procesando ciclo {ciclo.id}: {e}")

    # Convertir datos agregados a lista para el Excel
    resultado = []
    for (producto, fecha), valores in datos_agregados.items():
        resultado.append([
            producto, 
            f"{valores['peso']} kg", 
            f"{valores['tiempo']} minutos", 
            fecha
        ])
    
    # Ordenar por producto y fecha para mejor visualización
    resultado.sort(key=lambda x: (x[0], x[3]))

    # Crear el archivo Excel
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reporte Graficos"

    try:
        logoPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "cremona.png")
        img = Image(logoPath)
        img.width = 280
        img.height = 70
        sheet.add_image(img, 'D1')
    except Exception as e:
        print(f"Error al cargar la imagen: {e}")
        # Continuar sin la imagen

    sheet.append(["REPORTE: PRODUCTOS POR DÍA"])
    producto_cell = sheet.cell(row=sheet.max_row, column=1)
    producto_cell.font = Font(bold=True, size=20)

    sheet.append(["Fecha Inicio:", fecha_inicio.strftime("%d/%m/%Y")])
    fechaInicio_cell = sheet.cell(row=sheet.max_row, column=1)
    fechaInicio_cell.font = Font(bold=True, size=12)
    sheet.append(["Fecha Fin:", fecha_fin.strftime("%d/%m/%Y")])
    fechaFin_cell = sheet.cell(row=sheet.max_row, column=1)
    fechaFin_cell.font = Font(bold=True, size=12)

    # Nuevos encabezados para el formato solicitado
    headers = ["Producto", "Peso Desmoldado", "Tiempo Total Desmolde", "Fecha"]
    sheet.append(headers)

    # Aplicar formato a los encabezados
    header_fill = PatternFill(start_color="145f82", end_color="145f82", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)  

    for col in range(1, len(headers) + 1):
        cell = sheet.cell(row=sheet.max_row, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    start_row = sheet.max_row + 1

    # Agregar datos al Excel
    for fila in resultado:
        sheet.append(fila)

    # Crear tabla
    end_row = sheet.max_row
    start_col = 1
    end_col = len(headers)
    table_range = f"{sheet.cell(row=start_row - 1, column=start_col).coordinate}:{sheet.cell(row=end_row, column=end_col).coordinate}"
    table_nombre = "GraficoProductividadDiaria"
    tabla = Table(displayName=table_nombre, ref=table_range)
    style = TableStyleInfo(showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=True)
    tabla.tableStyleInfo = style

    # Agregar la tabla a la hoja
    sheet.add_table(tabla)
    sheet.append([])

    # Ajustar ancho de columnas
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

def get_lista_total_ciclos_productos(db, fecha_inicio:date, fecha_fin:date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

    print(f"Fecha inicio: {fecha_inicio}, Fecha fin: {fecha_fin}")

    listaResultado = {}

    tablaBDD = (
        db.query(CicloDesmoldeo, RecetarioXCiclo, Recetario)
        .join(RecetarioXCiclo, CicloDesmoldeo.id == RecetarioXCiclo.id_ciclo_desmoldeo)
        .join(Recetario, RecetarioXCiclo.id_recetario == Recetario.id)
        .filter(CicloDesmoldeo.fecha_fin.between(fecha_inicio, fecha_fin))
        .all()
    )
    registro = defaultdict(lambda: {"fecha_fin":"","PesoDiarioProducto":0})
    listaPeso = []

    for ciclo, recetaXCiclo, receta in tablaBDD:
        fecha = ciclo.fecha_fin.strftime("%Y-%m-%d")
        peso = ciclo.pesoDesmoldado

        # Si la receta ya está agregada, sumamos el peso
        registro = next((item for item in listaPeso if item["fecha_fin"] == fecha), None)
        if registro:
            registro["PesoDiarioProducto"] += peso
        else:
            listaPeso.append({"fecha_fin": fecha, "PesoDiarioProducto": peso})
    listaResultado["pesoProducto"] = listaPeso

    grouped_by_day = defaultdict(int)

    for ciclo, recetaXCiclo, receta in tablaBDD:
        dia = ciclo.fecha_fin.strftime("%Y-%m-%d")
        grouped_by_day[dia] += 1

    listaResultado["ciclos"] = [
        {"fecha_fin": fecha, "CiclosCompletados": count} 
        for fecha, count in grouped_by_day.items()
    ]

    return listaResultado