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

def buscarCiclos1_con_tiempo_util(idReceta, listaRecetaXCiclo, listaReceta_dic, listaCiclos_dic):
    def calcular_tiempo_util(tiempo_desmolde_str, tiempo_pausado_str):
        """Calcula el tiempo útil restando el tiempo pausado del tiempo de desmolde"""
        try:
            # Procesar tiempo de desmolde
            if not tiempo_desmolde_str or tiempo_desmolde_str == "" or tiempo_desmolde_str is None:
                tiempo_desmolde_str = "00:00"
            tiempo_desmolde_str = str(tiempo_desmolde_str).strip()
            if tiempo_desmolde_str == "None" or tiempo_desmolde_str == "" or tiempo_desmolde_str == "0":
                tiempo_desmolde_str = "00:00"
            
            # Procesar tiempo pausado
            if not tiempo_pausado_str or tiempo_pausado_str == "" or tiempo_pausado_str is None:
                tiempo_pausado_str = "00:00"
            tiempo_pausado_str = str(tiempo_pausado_str).strip()
            if tiempo_pausado_str == "None" or tiempo_pausado_str == "" or tiempo_pausado_str == "0":
                tiempo_pausado_str = "00:00"
            
            # Convertir tiempo de desmolde a minutos
            partes_desmolde = tiempo_desmolde_str.split(':')
            minutos_desmolde = 0
            if len(partes_desmolde) == 2:
                minutos_desmolde = int(partes_desmolde[0])
                segundos_desmolde = int(partes_desmolde[1])
                # Convertir segundos a minutos (redondeando hacia arriba si hay segundos)
                minutos_extra = segundos_desmolde // 60
                segundos_restantes = segundos_desmolde % 60
                minutos_desmolde = minutos_desmolde + minutos_extra
                # Si hay segundos restantes, sumar 1 minuto más
                if segundos_restantes > 0:
                    minutos_desmolde += 1
            
            # Convertir tiempo pausado a minutos
            partes_pausado = tiempo_pausado_str.split(':')
            minutos_pausado = 0
            if len(partes_pausado) == 2:
                minutos_pausado = int(partes_pausado[0])
                segundos_pausado = int(partes_pausado[1])
                # Convertir segundos a minutos (redondeando hacia arriba si hay segundos)
                minutos_extra = segundos_pausado // 60
                segundos_restantes = segundos_pausado % 60
                minutos_pausado = minutos_pausado + minutos_extra
                # Si hay segundos restantes, sumar 1 minuto más
                if segundos_restantes > 0:
                    minutos_pausado += 1
            
            # Calcular tiempo útil (desmolde - pausado)
            minutos_util = max(0, minutos_desmolde - minutos_pausado)
            
            # Convertir a formato hh:mm
            horas = minutos_util // 60
            minutos_finales = minutos_util % 60
            
            return f"{horas:02d}:{minutos_finales:02d}"
            
        except (ValueError, AttributeError, TypeError) as e:
            print(f"Error calculando tiempo útil - Desmolde: '{tiempo_desmolde_str}', Pausado: '{tiempo_pausado_str}': {e}")
            return "00:00"
    
    return [
        {
            "id_ciclo": recetaXCiclo.id_ciclo_desmoldeo,
            "pesoTotal": listaCiclos_dic[recetaXCiclo.id_ciclo_desmoldeo].pesoDesmoldado,
            "tiempoTotal": calcular_tiempo_util(
                listaCiclos_dic[recetaXCiclo.id_ciclo_desmoldeo].tiempoDesmolde,
                listaCiclos_dic[recetaXCiclo.id_ciclo_desmoldeo].tiempoPausado
            )
        }
        for _, recetaXCiclo, _ in listaRecetaXCiclo
        if recetaXCiclo.id_recetario == idReceta and 
           listaCiclos_dic[recetaXCiclo.id_ciclo_desmoldeo].estadoMaquina in ["FINALIZADO", "CANCELADO"]
    ]

def convertir_horas_a_minutos(tiempo_horas_str):
    """Convierte tiempo en formato 'hh:mm' a minutos totales para operaciones matemáticas"""
    try:
        if not tiempo_horas_str or tiempo_horas_str == "00:00":
            return 0
        
        partes = tiempo_horas_str.split(':')
        if len(partes) == 2:
            horas = int(partes[0])
            minutos = int(partes[1])
            return (horas * 60) + minutos
        else:
            return 0
    except (ValueError, AttributeError, TypeError):
        return 0

def convertir_minutos_a_horas(minutos_totales):
    """Convierte minutos totales a formato 'hh:mm'"""
    try:
        horas = minutos_totales // 60
        minutos = minutos_totales % 60
        return f"{horas:02d}:{minutos:02d}"
    except (ValueError, TypeError):
        return "00:00"

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
        .filter(CicloDesmoldeo.fecha_inicio.between(fecha_inicio,fecha_fin))
        .filter(CicloDesmoldeo.estadoMaquina.in_(["FINALIZADO", "CANCELADO"]))
        .all()
    )

    # Calcular totales primero
    for ciclo, recetaXCiclo, receta in tablaCiclos:
        totalPeso += ciclo.pesoDesmoldado
        cantidadCiclosTotal += 1

    # Procesar cada receta UNA SOLA VEZ
    recetas_procesadas = set()
    for ciclo, recetaXCiclo, receta in tablaCiclos:
        if receta.id not in recetas_procesadas:
            recetas_procesadas.add(receta.id)
            
            # Modificar buscarCiclos1 para calcular tiempo útil
            listaBuscarCiclo = buscarCiclos1_con_tiempo_util(receta.id, tablaCiclos, {r.id: r for _,_, r in tablaCiclos}, {c.id: c for c, _, _ in tablaCiclos})

            pesoFinal = sum(cicloData["pesoTotal"] for cicloData in listaBuscarCiclo)
            # Convertir cada tiempo a minutos antes de sumar
            tiempoTotalMinutos = sum(convertir_horas_a_minutos(cicloData["tiempoTotal"]) for cicloData in listaBuscarCiclo)
            # Convertir el total de minutos de vuelta a formato hh:mm
            tiempoTotalCiclo = convertir_minutos_a_horas(tiempoTotalMinutos)

            productosRealizados[receta.id] = {
                "id_recetario": receta.id,
                "NombreProducto": receta.codigoProducto,
                "pesoTotal": pesoFinal,
                "cantidadCiclos": len(listaBuscarCiclo),
                "tiempoTotal": tiempoTotalCiclo,  # Ahora en formato "hh:mm"
            }
            
    respuestaProductividad["CantidadCiclosCorrectos"] = cantidadCiclosTotal
    respuestaProductividad["PesoTotalCiclos"] = totalPeso / 1000 # Total en Toneladas
    respuestaProductividad["ProductosRealizados"] = list(productosRealizados.values())

    return respuestaProductividad

def generarDocumentoXLMSProductividad(db, fecha_inicio:date, fecha_fin:date):
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())
    
    # Convertir fechas para usar con las funciones de export_excel.py
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")
    
    # Verificar si hay datos usando una consulta directa con el rango de fechas
    tablaCiclos = (
        db.query(CicloDesmoldeo, RecetarioXCiclo, Recetario)
        .join(RecetarioXCiclo, CicloDesmoldeo.id == RecetarioXCiclo.id_ciclo_desmoldeo)
        .join(Recetario, RecetarioXCiclo.id_recetario == Recetario.id)
        .filter(CicloDesmoldeo.fecha_inicio.between(fecha_inicio, fecha_fin))
        .filter(CicloDesmoldeo.estadoMaquina.in_(["FINALIZADO", "CANCELADO"]))
        .all()
    )
    
    # Obtener ids únicos de recetarios
    id_recetarios = list(set(recetaXCiclo.id_recetario for _, recetaXCiclo, _ in tablaCiclos))
    
    # Si no hay datos, crear Excel vacío
    if not id_recetarios:
        print(f"No se encontraron datos para las fechas: {fecha_inicio_str} - {fecha_fin_str}")
    
    workbook = Workbook()
    ws = workbook.active
    ws.title = "Productividad | EFA"

    # Cargar logo
    try:
        logoPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "cremonarecort.png")
        if os.path.exists(logoPath):
            from openpyxl.drawing.image import Image as XLImage
            img = XLImage(logoPath)
            img.height = 35
            img.width = 140
            ws.add_image(img, "F3")
    except Exception as e:
        print(f"Error al cargar la imagen: {e}")

    # Título principal
    ws.merge_cells("A1:F1")
    ws["A1"] = "RESUMEN DE PRODUCTIVIDAD | EFA ALIMENTOS"
    ws["A1"].font = Font(size=16, bold=True)
    ws["A1"].alignment = Alignment(horizontal="center")
    from openpyxl.styles import PatternFill
    ws["A1"].fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

    # Fechas
    ws["A3"] = "Fecha inicial de filtrado:"
    ws["A3"].font = Font(size=12, bold=True)
    ws["A4"] = "Fecha final de filtrado:"
    ws["A4"].font = Font(size=12, bold=True)
    ws["B3"] = fecha_inicio_str
    ws["B4"] = fecha_fin_str

    # Calcular datos usando la lógica local para el rango de fechas
    if id_recetarios:
        # Crear diccionarios para almacenar los datos calculados
        codigos_producto = {}
        cantidad_ciclos = {}
        pesos_totales = {}
        tiempos_totales = {}
        niveles_desmoldados = {}
        segundos_por_nivel = {}
        
        # Procesar cada receta UNA SOLA VEZ
        recetas_procesadas = set()
        for ciclo, recetaXCiclo, receta in tablaCiclos:
            if receta.id not in recetas_procesadas:
                recetas_procesadas.add(receta.id)
                
                ciclos_receta = [
                    (c, rxc, r) for c, rxc, r in tablaCiclos 
                    if rxc.id_recetario == receta.id
                ]
                
                codigos_producto[receta.id] = receta.codigoProducto
                
                cantidad_ciclos[receta.id] = len([
                    c for c, rxc, r in ciclos_receta
                ])
                
                # Peso total
                pesos_totales[receta.id] = sum(c.pesoDesmoldado for c, rxc, r in ciclos_receta)
                
                # Tiempo total (restando pausado)
                total_segundos = 0
                for c, rxc, r in ciclos_receta:
                    tiempo_desmolde_str = c.tiempoDesmolde or "00:00"
                    tiempo_pausado_str = c.tiempoPausado or "00:00"
                    
                    # Convertir tiempo de desmolde a segundos
                    partes_desmolde = tiempo_desmolde_str.split(":")
                    segundos_desmolde = 0
                    if len(partes_desmolde) == 2:  # mm:ss
                        segundos_desmolde = int(partes_desmolde[0]) * 60 + int(partes_desmolde[1])
                    elif len(partes_desmolde) == 3:  # hh:mm:ss
                        segundos_desmolde = int(partes_desmolde[0]) * 3600 + int(partes_desmolde[1]) * 60 + int(partes_desmolde[2])
                    
                    # Convertir tiempo pausado a segundos
                    partes_pausado = tiempo_pausado_str.split(":")
                    segundos_pausado = 0
                    if len(partes_pausado) == 2:  # mm:ss
                        segundos_pausado = int(partes_pausado[0]) * 60 + int(partes_pausado[1])
                    elif len(partes_pausado) == 3:  # hh:mm:ss
                        segundos_pausado = int(partes_pausado[0]) * 3600 + int(partes_pausado[1]) * 60 + int(partes_pausado[2])
                    
                    # Tiempo efectivo (desmolde - pausado)
                    tiempo_efectivo = max(0, segundos_desmolde - segundos_pausado)
                    total_segundos += tiempo_efectivo
                
                # Convertir segundos totales a formato hh:mm:ss
                horas = total_segundos // 3600
                minutos = (total_segundos % 3600) // 60
                segundos = total_segundos % 60
                tiempos_totales[receta.id] = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
                
                # Niveles desmoldados
                niveles_desmoldados[receta.id] = sum(rxc.cantidadNivelesFinalizado for c, rxc, r in ciclos_receta)
                
                # Segundos por nivel
                niveles = niveles_desmoldados[receta.id]
                if niveles > 0:
                    segundos_por_nivel[receta.id] = int(total_segundos / niveles)
                else:
                    segundos_por_nivel[receta.id] = "0"
    else:
        codigos_producto = {}
        cantidad_ciclos = {}
        pesos_totales = {}
        tiempos_totales = {}
        niveles_desmoldados = {}
        segundos_por_nivel = {}

    # Encabezados simplificados
    headers_cliente = [
        "Producto",
        "Cantidad de ciclos",
        "Peso total desmoldado [kg]",
        "Tiempo util desmoldado [HH:MM:SS]",
        "Niveles desmoldados\ncorrectamente",
        "Segundos/Nivel [seg]"
    ]
    
    # Añadir línea vacía y encabezados
    ws.append([])  # Línea vacía
    ws.append(headers_cliente)

    # Guardar la fila donde empiezan los encabezados para la definición de la tabla
    first_table_first_row = ws.max_row
    
    # Aplicar formato multilínea a los encabezados
    for col in range(1, len(headers_cliente) + 1):
        cell = ws.cell(row=first_table_first_row, column=col)
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    # Ajustar altura de la fila de encabezados
    ws.row_dimensions[first_table_first_row].height = 45
    
    if id_recetarios:
        # Ordenar id_recetarios de forma ascendente
        id_recetarios_ordenados = sorted(id_recetarios)
        for id_recetario in id_recetarios_ordenados:
            codigo_producto = codigos_producto.get(id_recetario, "DESCONOCIDO")
            ciclos = cantidad_ciclos.get(id_recetario, 0)
            peso_total = pesos_totales.get(id_recetario, 0.0)
            tiempo_total = tiempos_totales.get(id_recetario, "00:00:00")
            niveles = niveles_desmoldados.get(id_recetario, 0)
            seg_por_nivel = segundos_por_nivel.get(id_recetario, "0")
            
            ws.append([
                codigo_producto,    # Producto
                ciclos,             # Cantidad de ciclos
                peso_total,         # Peso total desmoldado
                tiempo_total,       # Tiempo total desmoldado
                niveles,            # Niveles desmoldados correctamente
                seg_por_nivel       # Segundos/Nivel
            ])
    else:
        # Si no hay datos, agregar una fila con "Sin datos"
        ws.append([
            "DESCONOCIDO",      # Producto
            0,                  # Cantidad de ciclos
            "0.0",             # Peso total desmoldado
            "00:00:00",         # Tiempo total desmoldado
            0,                  # Niveles desmoldados correctamente
            "0"                # Segundos/Nivel
        ])
    
    # Calcular y agregar fila de totales
    total_ciclos = sum(cantidad_ciclos.values())
    total_peso = sum(pesos_totales.values())
    
    # Calcular el tiempo total en segundos
    total_segundos = 0
    for tiempo in tiempos_totales.values():
        partes = tiempo.split(":")
        segundos = int(partes[0]) * 3600 + int(partes[1]) * 60 + int(partes[2])
        total_segundos += segundos
        
    # Convertir segundos totales a formato hh:mm:ss
    horas_total = total_segundos // 3600
    minutos_total = (total_segundos % 3600) // 60
    segundos_total = total_segundos % 60
    tiempo_total_formato = f"{horas_total:02d}:{minutos_total:02d}:{segundos_total:02d}"
    
    # Calcular el total de niveles desmoldados
    total_niveles = sum(niveles_desmoldados.values())
    
    # Calcular segundos por nivel total
    segundos_por_nivel_total = "0"
    if total_niveles > 0:
        segundos_por_nivel_total = int(total_segundos / total_niveles)
    
    # Agregar fila de totales
    ws.append([
        "TOTALES",            # Producto
        total_ciclos,         # Cantidad de ciclos
        total_peso,           # Peso total desmoldado
        tiempo_total_formato, # Tiempo total desmoldado
        total_niveles,        # Niveles desmoldados correctamente
        segundos_por_nivel_total  # Segundos/Nivel
    ])
    
    # Dar formato a la fila de totales
    fila_totales = ws.max_row
    ws.row_dimensions[fila_totales].height = 30
    
    # Aplicar estilo negrita a la fila de totales
    from openpyxl.styles import Border, Side
    for col in range(1, 7):  # 6 columnas (A-F)
        cell = ws.cell(row=fila_totales, column=col)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(vertical='center')
        
        # Añadir un borde superior para destacar que es una fila de totales
        thin_border = Border(top=Side(style='thin'))
        cell.border = thin_border
    
    # Crear la tabla
    first_table_last_row = ws.max_row
    
    # Agregar la tabla
    from openpyxl.worksheet.table import Table, TableStyleInfo
    first_table = Table(displayName="ResumenProductividadCliente", ref=f"A{first_table_first_row}:F{first_table_last_row}")
    first_style = TableStyleInfo(
        name="TableStyleMedium9", showFirstColumn=False,
        showLastColumn=False, showRowStripes=True, showColumnStripes=False
    )
    first_table.tableStyleInfo = first_style
    ws.add_table(first_table)
    
    # Ajustar ancho de columnas
    for col in ws.columns:
        max_data_length = 0
        max_header_length = 0
        column = None
        is_header_multiline = False
        
        for cell in col:
            if hasattr(cell, "column_letter"):
                column = cell.column_letter
            else:
                continue
                
            try:
                if cell.value:
                    cell_str = str(cell.value)
                    
                    # Detectar si es un encabezado (filas 5-7 típicamente contienen encabezados)
                    if 5 <= cell.row <= 8 and ('[' in cell_str or 'Tiempo' in cell_str or 'Nivel' in cell_str or 'Peso' in cell_str):
                        # Es un encabezado
                        if '\n' in cell_str:
                            lines = cell_str.split('\n')
                            max_header_length = max(len(line) for line in lines)
                            is_header_multiline = True
                        else:
                            max_header_length = len(cell_str)
                    else:
                        # Es dato normal
                        if cell.row > 8:  # Evitar títulos y fechas
                            max_data_length = max(max_data_length, len(cell_str))
            except:
                pass
        
        if column:
            # Establecer ancho fijo de 25 para la primera columna (A)
            if column == "A":
                final_width = 25
            else:
                # Calcular ancho basándose en el contenido más largo (header vs datos)
                content_width = max(max_header_length, max_data_length)
                
                # Establecer rangos específicos por tipo de columna
                if column == "B":
                    # Para columna Producto, usar el mayor entre header y contenido, con mínimo 10
                    final_width = min(max(content_width + 2, 10), 25)
                elif "Tiempo" in str(max_header_length) or "MM:SS" in str(max_header_length):
                    final_width = 12  # Columnas de tiempo
                elif is_header_multiline:
                    # Para encabezados multilínea, usar la línea más larga + pequeño margen
                    final_width = min(max(max_header_length + 2, 10), 20)
                elif "[kg]" in str(ws[column + "6"].value or "") or "Peso" in str(ws[column + "6"].value or ""):
                    final_width = min(max(content_width + 2, 12), 16)  # Columnas de peso
                elif "[seg]" in str(ws[column + "6"].value or ""):
                    final_width = 21  # Segundos/Nivel
                else:
                    final_width = min(max(content_width + 2, 10), 25)  # Otras columnas
            
            ws.column_dimensions[column].width = final_width

    # Guardar en BytesIO y retornar
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
        .filter(CicloDesmoldeo.fecha_inicio.between(fecha_inicio, fecha_fin))
        .filter(CicloDesmoldeo.estadoMaquina.in_(["FINALIZADO", "CANCELADO"]))
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
    print(f"Fechas recibidas - Inicio: {fecha_inicio}, Fin: {fecha_fin}")
    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    fecha_fin = datetime.combine(fecha_fin, datetime.max.time())
    
    print(f"Buscando ciclos entre {fecha_inicio} y {fecha_fin}")

    # Convertir fechas para usar con las funciones de export_excel.py
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")
    
    # Verificar si hay datos usando una consulta directa con el rango de fechas
    tablaCiclos = (
        db.query(CicloDesmoldeo, RecetarioXCiclo, Recetario)
        .join(RecetarioXCiclo, CicloDesmoldeo.id == RecetarioXCiclo.id_ciclo_desmoldeo)
        .join(Recetario, RecetarioXCiclo.id_recetario == Recetario.id)
        .filter(CicloDesmoldeo.fecha_inicio.between(fecha_inicio, fecha_fin))
        .filter(CicloDesmoldeo.estadoMaquina.in_(["FINALIZADO", "CANCELADO"]))
        .all()
    )
    
    # Si no hay datos, crear Excel vacío
    if not tablaCiclos:
        print(f"No se encontraron datos para las fechas: {fecha_inicio_str} - {fecha_fin_str}")

    # Crear el archivo Excel
    workbook = Workbook()
    ws = workbook.active
    ws.title = "Torres | EFA"

    # Cargar logo
    try:
        logoPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "cremonarecort.png")
        if os.path.exists(logoPath):
            from openpyxl.drawing.image import Image as XLImage
            img = XLImage(logoPath)
            img.height = 35
            img.width = 140
            ws.add_image(img, "L3")
    except Exception as e:
        print(f"Error al cargar la imagen: {e}")

    # Título principal
    ws.merge_cells("A1:M1")
    ws["A1"] = "RESUMEN DE PRODUCTIVIDAD POR TORRE | EFA ALIMENTOS"
    ws["A1"].font = Font(size=16, bold=True)
    ws["A1"].alignment = Alignment(horizontal="center")
    from openpyxl.styles import PatternFill
    ws["A1"].fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

    # Fechas
    ws["A3"] = "Fecha inicial de filtrado:"
    ws["A3"].font = Font(size=12, bold=True)
    ws["A4"] = "Fecha final de filtrado:"
    ws["A4"].font = Font(size=12, bold=True)
    ws["B3"] = fecha_inicio_str
    ws["B4"] = fecha_fin_str

    # Encabezados para la tabla por torre (igual que la segunda tabla del export_excel.py)
    headers_torre_cliente = [
        "ID Ciclo",
        "Producto",
        "Torre",
        "Niveles\nDesmoldados",
        "Niveles\nSeleccionados",
        "Peso Desmoldado [kg]",
        "Tipo de Fin",
        "Cinta de\nDesmolde",
        "Inicio [AAAA-MM-DD HH:MM:SS]",
        "Fin [AAAA-MM-DD HH:MM:SS]",
        "Tiempo Desmolde\n[MM:SS]",
        "Tiempo Pausado\n[MM:SS]",
        "Tiempo Útil\n[MM:SS]"
    ]
    
    # Añadir línea vacía y encabezados
    ws.append([])  # Línea vacía
    ws.append(headers_torre_cliente)

    # Guardar la fila donde empiezan los encabezados para la definición de la tabla
    first_table_first_row = ws.max_row
    
    # Aplicar formato multilínea a los encabezados
    for col in range(1, len(headers_torre_cliente) + 1):
        cell = ws.cell(row=first_table_first_row, column=col)
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    # Ajustar altura de la fila de encabezados
    ws.row_dimensions[first_table_first_row].height = 45
    
    # Función auxiliar para convertir tiempo a formato MM:SS
    def tiempo_a_mm_ss(tiempo_str):
        """Convierte tiempo en formato 'mm:ss' o 'hh:mm:ss' a formato 'MM:SS'."""
        if not tiempo_str or not isinstance(tiempo_str, str):
            return "00:00"
        
        try:
            partes = tiempo_str.split(":")
            if len(partes) == 2:  # mm:ss
                return f"{int(partes[0]):02d}:{int(partes[1]):02d}"
            elif len(partes) == 3:  # hh:mm:ss
                # Convertir hh:mm:ss a total de minutos y segundos
                total_minutos = int(partes[0]) * 60 + int(partes[1])
                segundos = int(partes[2])
                return f"{total_minutos:02d}:{segundos:02d}"
            else:
                return "00:00"
        except:
            return "00:00"

    # Función auxiliar para calcular tiempo útil
    def calcular_tiempo_util_mm_ss(tiempo_desmolde_str, tiempo_pausado_str):
        """Calcula el tiempo útil restando tiempo pausado del tiempo de desmolde, retorna en MM:SS."""
        if not tiempo_desmolde_str:
            return "00:00"
        
        tiempo_pausado_str = tiempo_pausado_str or "00:00"
        
        try:
            # Convertir tiempo de desmolde a segundos totales
            partes_desmolde = tiempo_desmolde_str.split(":")
            segundos_desmolde = 0
            if len(partes_desmolde) == 2:  # mm:ss
                segundos_desmolde = int(partes_desmolde[0]) * 60 + int(partes_desmolde[1])
            elif len(partes_desmolde) == 3:  # hh:mm:ss
                segundos_desmolde = int(partes_desmolde[0]) * 3600 + int(partes_desmolde[1]) * 60 + int(partes_desmolde[2])
            
            # Convertir tiempo pausado a segundos totales
            partes_pausado = tiempo_pausado_str.split(":")
            segundos_pausado = 0
            if len(partes_pausado) == 2:  # mm:ss
                segundos_pausado = int(partes_pausado[0]) * 60 + int(partes_pausado[1])
            elif len(partes_pausado) == 3:  # hh:mm:ss
                segundos_pausado = int(partes_pausado[0]) * 3600 + int(partes_pausado[1]) * 60 + int(partes_pausado[2])
            
            # Calcular tiempo útil
            segundos_util = max(0, segundos_desmolde - segundos_pausado)
            
            # Convertir a MM:SS
            minutos = segundos_util // 60
            segundos = segundos_util % 60
            
            return f"{minutos:02d}:{segundos:02d}"
            
        except:
            return "00:00"

    # Obtener datos detallados de los ciclos directamente de tablaCiclos
    if tablaCiclos:
        for ciclo, recetaXCiclo, receta in tablaCiclos:
            # Formatear fechas
            fecha_inicio = ciclo.fecha_inicio.strftime("%Y-%m-%d %H:%M:%S") if ciclo.fecha_inicio else "N/A"
            fecha_fin = ciclo.fecha_fin.strftime("%Y-%m-%d %H:%M:%S") if ciclo.fecha_fin else "N/A"
            
            # Obtener tiempos
            tiempo_pausado_str = ciclo.tiempoPausado or "00:00"
            tiempo_desmolde_str = ciclo.tiempoDesmolde or "00:00"
            
            # Convertir a formato MM:SS
            tiempo_pausado_mm_ss = tiempo_a_mm_ss(tiempo_pausado_str)
            tiempo_desmolde_mm_ss = tiempo_a_mm_ss(tiempo_desmolde_str)
            tiempo_util_mm_ss = calcular_tiempo_util_mm_ss(tiempo_desmolde_str, tiempo_pausado_str)
            
            # Obtener tipo de fin
            tipo_fin = ciclo.estadoMaquina or "N/A"
            
            # Obtener torre (necesitamos hacer el cálculo según la lógica del export_excel.py)
            torre_tag = "N/A"
            try:
                if recetaXCiclo.id_recetario == 1:
                    ntorre = ciclo.id_torre
                elif recetaXCiclo.id_recetario == 2:
                    if ciclo.id_torre <= 19:
                        ntorre = ciclo.id_torre + 13
                    else:
                        ntorre = ciclo.id_torre + 90
                elif recetaXCiclo.id_recetario == 3:
                    ntorre = ciclo.id_torre + 32
                elif recetaXCiclo.id_recetario == 4:
                    ntorre = ciclo.id_torre + 36
                elif recetaXCiclo.id_recetario == 5:
                    ntorre = ciclo.id_torre + 66
                elif recetaXCiclo.id_recetario == 6:
                    ntorre = ciclo.id_torre + 96
                elif recetaXCiclo.id_recetario == 7:
                    ntorre = ciclo.id_torre + 100
                elif recetaXCiclo.id_recetario == 8:
                    ntorre = ciclo.id_torre + 102
                else:
                    ntorre = ciclo.id_torre
                
                # Buscar la torre en la base de datos
                torre = (
                    db.query(Torre)
                    .filter(Torre.NTorre == ntorre)
                    .filter(Torre.id_recetario == recetaXCiclo.id_recetario)
                    .first()
                )
                
                if torre and torre.ActualizarTAG:
                    torre_tag = torre.ActualizarTAG
                
            except Exception as e:
                print(f"Error obteniendo torre: {e}")
            
            ws.append([
                ciclo.id,                              # ID Ciclo
                receta.codigoProducto or "DESCONOCIDO", # Producto
                torre_tag,                             # Torre
                recetaXCiclo.cantidadNivelesFinalizado or 0,  # Niveles Desmoldados
                recetaXCiclo.cantidadNivelesSeleccionados or 0, # Niveles Seleccionados
                ciclo.pesoDesmoldado or 0,             # Peso Desmoldado
                tipo_fin,                              # Tipo de Fin
                ciclo.bandaDesmolde or "N/A",          # Cinta de Desmolde
                fecha_inicio,                          # Inicio
                fecha_fin,                             # Fin
                tiempo_desmolde_mm_ss,                 # Tiempo Desmolde [MM:SS]
                tiempo_pausado_mm_ss,                  # Tiempo Pausado [MM:SS]
                tiempo_util_mm_ss                      # Tiempo Útil [MM:SS]
            ])
    else:
        # Si no hay datos, agregar una fila con "Sin datos"
        ws.append([
            "Sin datos",    # ID Ciclo
            "DESCONOCIDO",  # Producto
            "N/A",          # Torre
            0,              # Niveles Desmoldados
            0,              # Niveles Seleccionados
            0,              # Peso Desmoldado
            "N/A",          # Tipo de Fin
            "N/A",          # Cinta de Desmolde
            "N/A",          # Inicio
            "N/A",          # Fin
            "00:00",        # Tiempo Desmolde [MM:SS]
            "00:00",        # Tiempo Pausado [MM:SS]
            "00:00"         # Tiempo Útil [MM:SS]
        ])
    
    # Crear la tabla
    first_table_last_row = ws.max_row
    
    # Aplicar formato de color rojo claro a las filas con "CANCELADO AL INICIAR"
    from openpyxl.styles import PatternFill
    light_red_fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
    
    # Recorrer las filas de datos (excluyendo encabezados)
    for row_num in range(first_table_first_row + 1, first_table_last_row + 1):
        tipo_fin_cell = ws[f"G{row_num}"]  # Columna G es "Tipo de Fin"
        if tipo_fin_cell.value == "CANCELADO AL INICIAR":
            # Aplicar color de fondo rojo claro a toda la fila
            for col_num in range(1, 14):  # Columnas A-M (13 columnas)
                cell = ws.cell(row=row_num, column=col_num)
                cell.fill = light_red_fill
    
    # Agregar la tabla
    from openpyxl.worksheet.table import Table, TableStyleInfo
    first_table = Table(displayName="ResumenProductividadTorreCliente", ref=f"A{first_table_first_row}:M{first_table_last_row}")
    first_style = TableStyleInfo(
        name="TableStyleMedium9", showFirstColumn=False,
        showLastColumn=False, showRowStripes=True, showColumnStripes=False
    )
    first_table.tableStyleInfo = first_style
    ws.add_table(first_table)
    
    # Ajustar ancho de columnas
    for col in ws.columns:
        max_data_length = 0
        max_header_length = 0
        column = None
        is_header_multiline = False
        
        for cell in col:
            if hasattr(cell, "column_letter"):
                column = cell.column_letter
            else:
                continue
                
            try:
                if cell.value:
                    cell_str = str(cell.value)
                    
                    # Detectar si es un encabezado (filas 5-7 típicamente contienen encabezados)
                    if 5 <= cell.row <= 8 and ('[' in cell_str or 'Tiempo' in cell_str or 'Nivel' in cell_str or 'Peso' in cell_str or 'ID' in cell_str):
                        # Es un encabezado
                        if '\n' in cell_str:
                            lines = cell_str.split('\n')
                            max_header_length = max(len(line) for line in lines)
                            is_header_multiline = True
                        else:
                            max_header_length = len(cell_str)
                    else:
                        # Es dato normal
                        if cell.row > 8:  # Evitar títulos y fechas
                            max_data_length = max(max_data_length, len(cell_str))
            except:
                pass
        
        if column:
            # Establecer ancho fijo de 25 para la primera columna (A)
            if column == "A":
                final_width = 25
            else:
                # Calcular ancho basándose en el contenido más largo (header vs datos)
                content_width = max(max_header_length, max_data_length)
                
                # Establecer rangos específicos por tipo de columna
                if column == "B":
                    # Para columna Producto, usar el mayor entre header y contenido, con mínimo 10
                    final_width = min(max(content_width + 2, 10), 25)
                elif "Tiempo" in str(max_header_length) or "MM:SS" in str(max_header_length):
                    final_width = 12  # Columnas de tiempo
                elif is_header_multiline:
                    # Para encabezados multilínea, usar la línea más larga + pequeño margen
                    final_width = min(max(max_header_length + 2, 10), 20)
                elif "[kg]" in str(ws[column + "6"].value or "") or "Peso" in str(ws[column + "6"].value or ""):
                    final_width = min(max(content_width + 2, 12), 16)  # Columnas de peso
                elif "ID" in str(ws[column + "6"].value or ""):
                    final_width = 10  # Columnas de ID
                else:
                    final_width = min(max(content_width + 2, 10), 25)  # Otras columnas
            
            ws.column_dimensions[column].width = final_width

    # Guardar en BytesIO y retornar
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
        .filter(CicloDesmoldeo.fecha_inicio.between(fecha_inicio, fecha_fin))
        .filter(CicloDesmoldeo.estadoMaquina.in_(["FINALIZADO", "CANCELADO"]))
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