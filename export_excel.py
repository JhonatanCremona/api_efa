import os
import pandas as pd
from config.db import SessionLocal
from sqlalchemy import text
import logging
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from dotenv import load_dotenv
from datetime import datetime

logger = logging.getLogger("uvicorn")
load_dotenv()
TIEMPO_EXCEL = int(os.getenv("TIEMPO_EXCEL", 1))

def normalizar_tiempo(tiempo_str):
    """Convierte 'mm:ss' o 'hh:mm:ss' a 'hh:mm:ss'."""
    if not isinstance(tiempo_str, str):
        tiempo_str = str(tiempo_str)
    partes = tiempo_str.split(":")
    if len(partes) == 2:
        return f"00:{partes[0].zfill(2)}:{partes[1].zfill(2)}"
    elif len(partes) == 3:
        return f"{partes[0].zfill(2)}:{partes[1].zfill(2)}:{partes[2].zfill(2)}"
    else:
        try:
            segundos = int(float(tiempo_str))
            return str(pd.to_timedelta(segundos, unit="s"))
        except Exception:
            return "00:00:00"

def tiempo_a_minutos(tiempo_str):
    """Convierte tiempo en formato 'mm:ss' o 'hh:mm:ss' a minutos."""
    if not tiempo_str or not isinstance(tiempo_str, str):
        return 0
    
    try:
        partes = tiempo_str.split(":")
        if len(partes) == 2:  # mm:ss
            return int(partes[0]) + (int(partes[1]) / 60)
        elif len(partes) == 3:  # hh:mm:ss
            return int(partes[0]) * 60 + int(partes[1]) + (int(partes[2]) / 60)
        else:
            return 0
    except:
        return 0

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

def obtener_id_recetario_por_fecha(fecha):
    session = SessionLocal()
    try:
        query = text("""
            SELECT DISTINCT rxc.id_recetario
            FROM recetarioxciclo rxc
            JOIN ciclodesmoldeo cd ON rxc.id_ciclo_desmoldeo = cd.id
            WHERE DATE(cd.fecha_inicio) = :fecha
        """)
        result = session.execute(query, {"fecha": fecha})
        ids = [row[0] for row in result.fetchall()]
        return ids
    finally:
        session.close()

def obtener_codigos_producto_por_ids_recetario(id_recetarios):
    if not id_recetarios:
        return {}
    
    session = SessionLocal()
    try:
        # Convertir la lista a una cadena separada por comas para la consulta SQL
        ids_str = ", ".join(str(id) for id in id_recetarios)
        
        query = text(f"""
            SELECT id, codigoProducto
            FROM recetario
            WHERE id IN ({ids_str})
        """)
        
        result = session.execute(query)
        # Crear un diccionario {id_recetario: codigoProducto}
        return {row[0]: row[1] for row in result.fetchall()}
    finally:
        session.close()

def obtener_cantidad_ciclos_por_recetario(fecha):
    session = SessionLocal()
    try:
        query = text("""
            SELECT rxc.id_recetario, COUNT(DISTINCT rxc.id_ciclo_desmoldeo) as cantidad_ciclos
            FROM recetarioxciclo rxc
            JOIN ciclodesmoldeo cd ON rxc.id_ciclo_desmoldeo = cd.id
            WHERE DATE(cd.fecha_inicio) = :fecha
            GROUP BY rxc.id_recetario
        """)
        result = session.execute(query, {"fecha": fecha})
        # Crear un diccionario {id_recetario: cantidad_ciclos}
        return {row[0]: row[1] for row in result.fetchall()}
    finally:
        session.close()

def obtener_ciclos_cancelados_por_recetario(fecha):
    session = SessionLocal()
    try:
        query = text("""
            SELECT rxc.id_recetario, COUNT(DISTINCT rxc.id_ciclo_desmoldeo) as ciclos_cancelados
            FROM recetarioxciclo rxc
            JOIN ciclodesmoldeo cd ON rxc.id_ciclo_desmoldeo = cd.id
            WHERE DATE(cd.fecha_inicio) = :fecha
            AND (cd.estadoMaquina = 'CANCELADO' OR cd.estadoMaquina = 'CANCELADO AL INICIAR')
            GROUP BY rxc.id_recetario
        """)
        result = session.execute(query, {"fecha": fecha})
        # Crear un diccionario {id_recetario: ciclos_cancelados}
        return {row[0]: row[1] for row in result.fetchall()}
    finally:
        session.close()

def obtener_peso_total_por_recetario(fecha):
    """Obtiene el peso total desmoldado para cada id_recetario en una fecha específica."""
    session = SessionLocal()
    try:
        query = text("""
            SELECT rxc.id_recetario, SUM(cd.pesoDesmoldado) as peso_total
            FROM recetarioxciclo rxc
            JOIN ciclodesmoldeo cd ON rxc.id_ciclo_desmoldeo = cd.id
            WHERE DATE(cd.fecha_inicio) = :fecha
            GROUP BY rxc.id_recetario
        """)
        result = session.execute(query, {"fecha": fecha})
        # Crear un diccionario {id_recetario: peso_total}
        return {row[0]: row[1] for row in result.fetchall()}
    finally:
        session.close()

def obtener_tiempo_total_por_recetario(fecha):
    session = SessionLocal()
    try:
        query = text("""
            SELECT rxc.id_recetario, cd.tiempoDesmolde, cd.tiempoPausado
            FROM recetarioxciclo rxc
            JOIN ciclodesmoldeo cd ON rxc.id_ciclo_desmoldeo = cd.id
            WHERE DATE(cd.fecha_inicio) = :fecha
        """)
        result = session.execute(query, {"fecha": fecha})
        
        # Agrupar tiempos por id_recetario
        tiempos_por_recetario = {}
        for row in result.fetchall():
            id_recetario = row[0]
            tiempo_desmolde_str = row[1]
            tiempo_pausado_str = row[2] or "00:00"  # Si es NULL, usar "00:00"
            
            if id_recetario not in tiempos_por_recetario:
                tiempos_por_recetario[id_recetario] = []
            
            tiempos_por_recetario[id_recetario].append({
                'desmolde': tiempo_desmolde_str,
                'pausado': tiempo_pausado_str
            })
        
        # Calcular el tiempo total para cada recetario
        totales = {}
        for id_recetario, tiempos in tiempos_por_recetario.items():
            segundos_totales = 0
            for tiempo_info in tiempos:
                # Convertir tiempo de desmolde a segundos
                tiempo_desmolde = tiempo_info['desmolde']
                partes_desmolde = tiempo_desmolde.split(":")
                segundos_desmolde = 0
                if len(partes_desmolde) == 2:  # mm:ss
                    segundos_desmolde = int(partes_desmolde[0]) * 60 + int(partes_desmolde[1])
                elif len(partes_desmolde) == 3:  # hh:mm:ss
                    segundos_desmolde = int(partes_desmolde[0]) * 3600 + int(partes_desmolde[1]) * 60 + int(partes_desmolde[2])
                
                # Convertir tiempo pausado a segundos
                tiempo_pausado = tiempo_info['pausado']
                partes_pausado = tiempo_pausado.split(":")
                segundos_pausado = 0
                if len(partes_pausado) == 2:  # mm:ss
                    segundos_pausado = int(partes_pausado[0]) * 60 + int(partes_pausado[1])
                elif len(partes_pausado) == 3:  # hh:mm:ss
                    segundos_pausado = int(partes_pausado[0]) * 3600 + int(partes_pausado[1]) * 60 + int(partes_pausado[2])
                
                # Restar tiempo pausado del tiempo de desmolde y sumar al total
                tiempo_efectivo = segundos_desmolde - segundos_pausado
                # Asegurar que no sea negativo
                tiempo_efectivo = max(0, tiempo_efectivo)
                segundos_totales += tiempo_efectivo
            
            # Convertir segundos totales a formato hh:mm:ss
            horas = segundos_totales // 3600
            minutos = (segundos_totales % 3600) // 60
            segundos = segundos_totales % 60
            
            totales[id_recetario] = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
        
        return totales
    finally:
        session.close()

def obtener_niveles_desmoldados_por_recetario(fecha):
    session = SessionLocal()
    try:
        query = text("""
            SELECT rxc.id_recetario, SUM(rxc.cantidadNivelesFinalizado) as niveles_desmoldados
            FROM recetarioxciclo rxc
            JOIN ciclodesmoldeo cd ON rxc.id_ciclo_desmoldeo = cd.id
            WHERE DATE(cd.fecha_inicio) = :fecha
            GROUP BY rxc.id_recetario
        """)
        result = session.execute(query, {"fecha": fecha})
        # Crear un diccionario {id_recetario: niveles_desmoldados}
        return {row[0]: row[1] for row in result.fetchall()}
    finally:
        session.close()

def obtener_segundos_por_nivel_por_recetario(tiempos_totales, niveles_desmoldados):
    """
    Calcula los segundos por nivel para cada recetario.
    Args:
        tiempos_totales: Diccionario {id_recetario: "hh:mm:ss"}
        niveles_desmoldados: Diccionario {id_recetario: cantidad_niveles}
    Returns:
        Diccionario {id_recetario: "X seg"}
    """
    segundos_por_nivel = {}
    
    for id_recetario, tiempo_total in tiempos_totales.items():
        niveles = niveles_desmoldados.get(id_recetario, 0)
        
        try:
            # Convertir tiempo_total (hh:mm:ss) a segundos totales
            tiempo_partes = tiempo_total.split(":")
            segundos_totales = int(tiempo_partes[0]) * 3600 + int(tiempo_partes[1]) * 60 + int(tiempo_partes[2])
            
            # Calcular segundos por nivel (si hay niveles)
            if niveles > 0:
                segundos_por_nivel[id_recetario] = f"{int(segundos_totales / niveles)} seg"
            else:
                segundos_por_nivel[id_recetario] = "N/A seg"
        except Exception:
            segundos_por_nivel[id_recetario] = "N/A seg"
    
    return segundos_por_nivel

def calcular_porcentaje_fallas(ciclos_totales, ciclos_cancelados):
    """
    Calcula el porcentaje de fallas para cada recetario.
    Args:
        ciclos_totales: Diccionario {id_recetario: total_ciclos}
        ciclos_cancelados: Diccionario {id_recetario: ciclos_cancelados}
    Returns:
        Diccionario {id_recetario: porcentaje_fallas}
    """
    porcentajes = {}
    
    for id_recetario, total in ciclos_totales.items():
        cancelados = ciclos_cancelados.get(id_recetario, 0)
        
        if total > 0:
            porcentajes[id_recetario] = round((cancelados / total) * 100, 2)
        else:
            porcentajes[id_recetario] = 0
    
    return porcentajes

def obtener_detalles_ciclos_por_fecha(fecha):
    """
    Obtiene los detalles de todos los ciclos para una fecha específica.
    Args:
        fecha: Fecha en formato "YYYY-MM-DD"
    Returns:
        Lista de tuplas con los detalles de los ciclos
    """
    session = SessionLocal()
    try:
        query = text("""
            SELECT 
                cd.id AS id_ciclo, 
                r.codigoProducto AS producto,
                t.ActualizarTAG AS torre,
                rxc.cantidadNivelesFinalizado AS niveles_desmoldados,
                rxc.cantidadNivelesSeleccionados AS niveles_seleccionados,
                cd.pesoDesmoldado AS peso_desmoldado,
                cd.estadoMaquina AS tipo_fin,
                cd.bandaDesmolde AS cinta_desmolde,
                cd.fecha_inicio AS inicio,
                cd.fecha_fin AS fin,
                cd.tiempoPausado AS tiempo_pausado,
                cd.tiempoDesmolde AS tiempo_total
            FROM ciclodesmoldeo cd
            JOIN recetarioxciclo rxc ON cd.id = rxc.id_ciclo_desmoldeo
            JOIN recetario r ON rxc.id_recetario = r.id
            LEFT JOIN torre t ON 
                t.NTorre = CASE rxc.id_recetario
                    WHEN 1 THEN cd.id_torre
                    WHEN 2 THEN 
                        CASE 
                            WHEN cd.id_torre <= 19 THEN cd.id_torre + 13
                            ELSE cd.id_torre + 91
                        END
                    WHEN 3 THEN cd.id_torre + 32
                    WHEN 4 THEN cd.id_torre + 36
                    WHEN 5 THEN cd.id_torre + 66
                    WHEN 6 THEN cd.id_torre + 96
                    WHEN 7 THEN cd.id_torre + 100
                    WHEN 8 THEN cd.id_torre + 102
                    ELSE cd.id_torre
                END
                AND t.id_recetario = rxc.id_recetario
            WHERE DATE(cd.fecha_inicio) = :fecha
        """)
        result = session.execute(query, {"fecha": fecha})
        return result.fetchall()
    finally:
        session.close()

def export_ciclodesmoldeo_to_excel(file_path, fecha_hoy):
    logger.info(f"Exportando datos de ciclodesmoldeo para la fecha: {fecha_hoy}")

    fecha_inicio = pd.to_datetime(fecha_hoy)
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")

    fecha_fin = pd.to_datetime(fecha_hoy)
    fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")
    
    # Verificar si hay datos antes de crear el Excel
    id_recetarios = obtener_id_recetario_por_fecha(fecha_inicio_str)
    
    # Si no hay datos, retornar False para indicar que no hay registros
    if not id_recetarios:
        logger.info(f"No se encontraron datos para la fecha: {fecha_hoy}")
        return False

    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Productividad | INGENIERIA"

        logo_path = os.path.join(os.path.dirname(__file__), "static", "cremonarecort.png")
        if os.path.exists(logo_path):
            img = XLImage(logo_path)
            img.height = 35
            img.width = 140
            ws.add_image(img, "H3")

        ws.merge_cells("A1:I1")
        ws["A1"] = "RESUMEN DE PRODUCTIVIDAD CREMINOX"
        ws["A1"].font = Font(size=16, bold=True)
        ws["A1"].alignment = Alignment(horizontal="center")
        ws["A1"].fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

        ws["A3"] = "Fecha inicial de filtrado:"
        ws["A3"].font = Font(size=12, bold=True)
        ws["A4"] = "Fecha final de filtrado"
        ws["A4"].font = Font(size=12, bold=True)
        ws["B3"] = fecha_inicio_str
        ws["B4"] = fecha_fin_str

        codigos_producto = obtener_codigos_producto_por_ids_recetario(id_recetarios)
        cantidad_ciclos = obtener_cantidad_ciclos_por_recetario(fecha_inicio_str)
        ciclos_cancelados = obtener_ciclos_cancelados_por_recetario(fecha_inicio_str)
        pesos_totales = obtener_peso_total_por_recetario(fecha_inicio_str)
        tiempos_totales = obtener_tiempo_total_por_recetario(fecha_inicio_str)
        niveles_desmoldados = obtener_niveles_desmoldados_por_recetario(fecha_inicio_str)
        
        # Calcular segundos por nivel y porcentaje de fallas
        segundos_por_nivel = obtener_segundos_por_nivel_por_recetario(tiempos_totales, niveles_desmoldados)
        porcentaje_fallas = calcular_porcentaje_fallas(cantidad_ciclos, ciclos_cancelados)

        # Añadir las nuevas columnas a los encabezados
        headers = [
            "ID Receta",
            "Producto",
            "Cantidad de ciclos",
            "Peso total desmoldado [kg]",
            "Tiempo util desmoldado [HH:MM:SS]",
            "Niveles desmoldados correctamente",
            "Segundos/Nivel",
            "Eficiencia bruta",   # Nueva columna (se deja vacía)
            "% Falla"             # Nueva columna con porcentaje de fallas
        ]
        ws.append([])  # Línea vacía
        ws.append(headers)

        if id_recetarios:
            for id_recetario in id_recetarios:
                codigo_producto = codigos_producto.get(id_recetario, "DESCONOCIDO")
                ciclos = cantidad_ciclos.get(id_recetario, 0)
                peso_total = pesos_totales.get(id_recetario, 0.0)
                tiempo_total = tiempos_totales.get(id_recetario, "00:00:00")
                niveles = niveles_desmoldados.get(id_recetario, 0)
                seg_por_nivel = segundos_por_nivel.get(id_recetario, "N/A seg")
                falla_porcentaje = porcentaje_fallas.get(id_recetario, 0)
                
                # Añadir las nuevas columnas en la fila
                ws.append([
                    str(id_recetario),
                    codigo_producto,
                    ciclos,
                    f"{peso_total} kg",
                    tiempo_total,
                    niveles,
                    seg_por_nivel,
                    "",                # Eficiencia bruta (vacía)
                    f"{falla_porcentaje}%"  # % Falla
                ])
        else:
            # Si no hay datos, agregar una fila con "Sin datos"
            ws.append([
                "Sin datos",
                "DESCONOCIDO",
                0,
                "0.0 kg",
                "00:00",
                0,
                "N/A seg",
                "",                # Eficiencia bruta (vacía)
                "0%"               # % Falla
            ])
            
        # Agregar la fila de totales
        # Calcular los totales
        total_ciclos = sum(cantidad_ciclos.values())
        total_peso = sum(pesos_totales.values())
        total_ciclos_cancelados = sum(ciclos_cancelados.values())
        
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
        segundos_por_nivel_total = "N/A seg"
        if total_niveles > 0:
            segundos_por_nivel_total = f"{int(total_segundos / total_niveles)} seg"
        
        # Calcular el porcentaje de fallas total (ciclos cancelados totales / ciclos totales * 100)
        porcentaje_falla_total = 0
        if total_ciclos > 0:
            porcentaje_falla_total = round((total_ciclos_cancelados / total_ciclos) * 100, 2)
        
        # Agregar la fila de totales
        ws.append([
            "TOTALES",            # ID Receta
            "",                   # Producto
            total_ciclos,         # Cantidad de ciclos
            f"{total_peso} kg",   # Peso total desmoldado
            tiempo_total_formato, # Tiempo total desmoldado
            total_niveles,        # Niveles desmoldados correctamente
            segundos_por_nivel_total,  # Segundos/Nivel
            "",                   # Eficiencia bruta (vacía)
            f"{porcentaje_falla_total}%"  # % Falla (total)
        ])
        
        # Dar formato a la fila de totales
        fila_totales = ws.max_row
        ws.row_dimensions[fila_totales].height = 30  # El doble de la altura normal
        
        # Aplicar estilo negrita a la fila de totales
        for col in range(1, 10):  # 9 columnas (A-I)
            cell = ws.cell(row=fila_totales, column=col)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(vertical='center')
            
            # Añadir un borde superior para destacar que es una fila de totales
            thin_border = Border(top=Side(style='thin'))
            cell.border = thin_border

        first_table_row = ws.max_row - len(id_recetarios or [1]) - 1  # La fila de encabezados
        last_table_row = ws.max_row  # La última fila de datos (incluyendo totales)

        # Actualizar la referencia de la tabla para incluir las nuevas columnas y la fila de totales
        table = Table(displayName="ResumenProductividad", ref=f"A{first_table_row}:I{last_table_row}")
        style = TableStyleInfo(
            name="TableStyleMedium9", showFirstColumn=False,
            showLastColumn=False, showRowStripes=True, showColumnStripes=False
        )
        table.tableStyleInfo = style
        ws.add_table(table)

        # ------------------ SEGUNDA TABLA: RESUMEN DE PRODUCTIVIDAD CLIENTE ------------------
        
        # Guardar la última fila de la primera tabla
        ultima_fila_primera_tabla = ws.max_row
        
        # Crear 2 filas vacías de separación explícitas (en lugar de usar append)
        for i in range(1, 3):
            nueva_fila = ultima_fila_primera_tabla + i
            for col in range(1, 10):  # Asegurarse de que todas las columnas estén vacías
                ws.cell(row=nueva_fila, column=col, value=None)
        
        # El título de la segunda tabla debe estar 2 filas después de la última fila de la primera tabla
        segunda_tabla_titulo_fila = ultima_fila_primera_tabla + 3
        
        ws.merge_cells(f"A{segunda_tabla_titulo_fila}:F{segunda_tabla_titulo_fila}")
        cell = ws.cell(row=segunda_tabla_titulo_fila, column=1)
        cell.value = "RESUMEN DE PRODUCTIVIDAD CLIENTE"
        cell.font = Font(size=16, bold=True)
        cell.alignment = Alignment(horizontal="center")
        cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        
        fecha_row = segunda_tabla_titulo_fila + 2  # Una fila vacía después del título
        subtitulo_row = segunda_tabla_titulo_fila + 3  # Una fila vacía después del título
        
        # Añadir la fecha
        ws.cell(row=fecha_row, column=1, value="Fecha inicial de filtrado:")
        ws.cell(row=fecha_row, column=1).font = Font(size=12, bold=True)
        ws.cell(row=fecha_row, column=2, value=fecha_inicio_str)

        ws.cell(row=subtitulo_row, column=1, value="Fecha final de filtrado:")
        ws.cell(row=subtitulo_row, column=1).font = Font(size=12, bold=True)
        ws.cell(row=subtitulo_row, column=2, value=fecha_fin_str)

        empty_row = subtitulo_row + 1
        
        # Insertar el segundo logo
        if os.path.exists(logo_path):
            img2 = XLImage(logo_path)
            img2.height = 35
            img2.width = 140
            ws.add_image(img2, f"F{fecha_row}")  # Logo alineado a la derecha

        # Añadir los encabezados simplificados (después de la fecha)
        headers_row = empty_row + 1  # Una fila vacía después de la fecha/logo
        
        headers_cliente = [
            "Producto",
            "Cantidad de ciclos",
            "Peso total desmoldado [kg]",
            "Tiempo util desmoldado [HH:MM:SS]",
            "Niveles desmoldados correctamente",
            "Segundos/Nivel"
        ]
        
        # Agregar encabezados
        for col, header in enumerate(headers_cliente, 1):
            ws.cell(row=headers_row, column=col, value=header)
                
        # Guardar la fila donde empiezan los encabezados para la definición de la tabla
        second_table_first_row = headers_row
        
        if id_recetarios:
            for id_recetario in id_recetarios:
                codigo_producto = codigos_producto.get(id_recetario, "DESCONOCIDO")
                ciclos = cantidad_ciclos.get(id_recetario, 0)
                peso_total = pesos_totales.get(id_recetario, 0.0)
                tiempo_total = tiempos_totales.get(id_recetario, "00:00:00")
                niveles = niveles_desmoldados.get(id_recetario, 0)
                seg_por_nivel = segundos_por_nivel.get(id_recetario, "N/A seg")
                
                # Añadir solo las columnas especificadas en la segunda tabla
                ws.append([
                    codigo_producto,    # Producto
                    ciclos,             # Cantidad de ciclos
                    f"{peso_total} kg", # Peso total desmoldado
                    tiempo_total,       # Tiempo total desmoldado
                    niveles,            # Niveles desmoldados correctamente
                    seg_por_nivel       # Segundos/Nivel
                ])
        else:
            # Si no hay datos, agregar una fila con "Sin datos"
            ws.append([
                "DESCONOCIDO",      # Producto
                0,                  # Cantidad de ciclos
                "0.0 kg",           # Peso total desmoldado
                "00:00",            # Tiempo total desmoldado
                0,                  # Niveles desmoldados correctamente
                "N/A seg"           # Segundos/Nivel
            ])
        
        # Agregar fila de totales a la segunda tabla
        ws.append([
            "TOTALES",            # Producto
            total_ciclos,         # Cantidad de ciclos
            f"{total_peso} kg",   # Peso total desmoldado
            tiempo_total_formato, # Tiempo total desmoldado
            total_niveles,        # Niveles desmoldados correctamente
            segundos_por_nivel_total  # Segundos/Nivel
        ])
        
        # Dar formato a la fila de totales de la segunda tabla
        fila_totales_segunda = ws.max_row
        ws.row_dimensions[fila_totales_segunda].height = 30  # El doble de la altura normal
        
        # Aplicar estilo negrita a la fila de totales de la segunda tabla
        for col in range(1, 7):  # 6 columnas (A-F)
            cell = ws.cell(row=fila_totales_segunda, column=col)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(vertical='center')
            
            # Añadir un borde superior para destacar que es una fila de totales
            thin_border = Border(top=Side(style='thin'))
            cell.border = thin_border
        
        # Crear la segunda tabla
        second_table_last_row = ws.max_row  # La última fila de datos (incluyendo totales)
        
        # Agregar la segunda tabla
        second_table = Table(displayName="ResumenProductividadCliente", ref=f"A{second_table_first_row}:F{second_table_last_row}")
        second_style = TableStyleInfo(
            name="TableStyleMedium9", showFirstColumn=False,
            showLastColumn=False, showRowStripes=True, showColumnStripes=False
        )
        second_table.tableStyleInfo = second_style
        ws.add_table(second_table)
        
        # ------------------ TERCERA PÁGINA: RESUMEN POR TORRE ------------------
        
        # Crear una nueva hoja
        ws_torre = wb.create_sheet("Torres | INGENIERIA")
        
        # Insertar logo en la nueva hoja
        if os.path.exists(logo_path):
            img3 = XLImage(logo_path)
            img3.height = 35
            img3.width = 140
            ws_torre.add_image(img3, "N3")

        # Encabezado de la nueva hoja
        ws_torre.merge_cells("A1:N1")  # Fusionar celdas para el título (14 columnas)
        ws_torre["A1"] = "RESUMEN DE PRODUCTIVIDAD POR TORRE CREMINOX"
        ws_torre["A1"].font = Font(size=16, bold=True)
        ws_torre["A1"].alignment = Alignment(horizontal="center")
        ws_torre["A1"].fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

        ws_torre["A3"] = "Fecha inicial de filtrado:"
        ws_torre["A3"].font = Font(size=12, bold=True)
        ws_torre["A4"] = "Fecha final de filtrado"
        ws_torre["A4"].font = Font(size=12, bold=True)
        ws_torre["B3"] = fecha_inicio_str
        ws_torre["B4"] = fecha_fin_str

        # Encabezados para la tabla por torre
        headers_torre = [
            "ID Ciclo",
            "Producto",
            "Torre",
            "Niveles Desmoldados",
            "Niveles Seleccionados",
            "Peso Desmoldado [kg]",
            "Tipo de Fin",
            "Cinta de Desmolde",
            "Inicio [AAAA-MM-DD HH:MM:SS]",
            "Fin [AAAA-MM-DD HH:MM:SS]",
            "Tiempo Desmolde [MM:SS]",
            "Tiempo Pausado [MM:SS]",
            "Tiempo Útil [MM:SS]",
            "Recuento de Fallas"
        ]
        
        # Añadir línea vacía y encabezados
        ws_torre.append([])  # Línea vacía
        ws_torre.append(headers_torre)
        
        # Guardar la fila donde empiezan los encabezados para la definición de la tabla
        torre_table_first_row = ws_torre.max_row
        
        # Obtener datos detallados de los ciclos
        detalles_ciclos = obtener_detalles_ciclos_por_fecha(fecha_inicio_str)
        
        # Contador de fallas acumulado
        contador_fallas = 0
        
        if detalles_ciclos:
            for ciclo in detalles_ciclos:
                # Formatear fechas
                fecha_inicio = ciclo[8].strftime("%Y-%m-%d %H:%M:%S") if ciclo[8] else "N/A"
                fecha_fin = ciclo[9].strftime("%Y-%m-%d %H:%M:%S") if ciclo[9] else "N/A"
                
                # Obtener tiempos directamente de la base
                tiempo_pausado_str = ciclo[10] or "00:00"
                tiempo_desmolde_str = ciclo[11] or "00:00"
                
                # Convertir a formato MM:SS
                tiempo_pausado_mm_ss = tiempo_a_mm_ss(tiempo_pausado_str)
                tiempo_desmolde_mm_ss = tiempo_a_mm_ss(tiempo_desmolde_str)
                tiempo_util_mm_ss = calcular_tiempo_util_mm_ss(tiempo_desmolde_str, tiempo_pausado_str)
                
                # Verificar si es una falla y determinar qué mostrar en la columna
                tipo_fin = ciclo[6] or "N/A"
                if tipo_fin in ["CANCELADO", "CANCELADO AL INICIAR"]:
                    contador_fallas += 1
                    valor_fallas = contador_fallas  # Mostrar el número solo cuando hay falla
                else:
                    valor_fallas = "-"  # Mostrar guión cuando no hay falla
                
                ws_torre.append([
                    ciclo[0],                  # ID Ciclo
                    ciclo[1] or "DESCONOCIDO", # Producto
                    ciclo[2] or "N/A",         # Torre
                    ciclo[3] or 0,             # Niveles Desmoldados
                    ciclo[4] or 0,             # Niveles Seleccionados
                    f"{ciclo[5]} kg" if ciclo[5] else "0.00 kg", # Peso Desmoldado
                    tipo_fin,                  # Tipo de Fin
                    ciclo[7] or "N/A",         # Cinta de Desmolde
                    fecha_inicio,              # Inicio
                    fecha_fin,                 # Fin
                    tiempo_desmolde_mm_ss,     # Tiempo Desmolde [MM:SS]
                    tiempo_pausado_mm_ss,      # Tiempo Pausado [MM:SS]
                    tiempo_util_mm_ss,         # Tiempo Útil [MM:SS]
                    valor_fallas               # Recuento de Fallas (número solo en fallas, "-" en el resto)
                ])
        else:
            # Si no hay datos, agregar una fila con "Sin datos"
            ws_torre.append([
                "Sin datos",    # ID Ciclo
                "DESCONOCIDO",  # Producto
                "N/A",          # Torre
                0,              # Niveles Desmoldados
                0,              # Niveles Seleccionados
                "0.00 kg",      # Peso Desmoldado
                "N/A",          # Tipo de Fin
                "N/A",          # Cinta de Desmolde
                "N/A",          # Inicio
                "N/A",          # Fin
                "00:00",        # Tiempo Desmolde [MM:SS]
                "00:00",        # Tiempo Pausado [MM:SS]
                "00:00",        # Tiempo Útil [MM:SS]
                "-"             # Recuento de Fallas
            ])
        
        # Definir la tabla de torre
        torre_table_last_row = ws_torre.max_row
        
        # Agregar la tabla de torre
        torre_table = Table(displayName="ResumenProductividadTorre", ref=f"A{torre_table_first_row}:N{torre_table_last_row}")
        torre_style = TableStyleInfo(
            name="TableStyleMedium9", showFirstColumn=False,
            showLastColumn=False, showRowStripes=True, showColumnStripes=False
        )
        torre_table.tableStyleInfo = torre_style
        ws_torre.add_table(torre_table)
        
        # ------------------ SEGUNDA TABLA: RESUMEN DE PRODUCTIVIDAD POR TORRE CLIENTE ------------------
        
        # Guardar la última fila de la primera tabla de torres
        ultima_fila_primera_tabla_torres = ws_torre.max_row
        
        # Crear 2 filas vacías de separación explícitas
        for i in range(1, 3):
            nueva_fila = ultima_fila_primera_tabla_torres + i
            for col in range(1, 15):  # Asegurarse de que todas las columnas estén vacías (14 columnas)
                ws_torre.cell(row=nueva_fila, column=col, value=None)
        
        # El título de la segunda tabla debe estar 2 filas después de la última fila de la primera tabla
        segunda_tabla_torres_titulo_fila = ultima_fila_primera_tabla_torres + 3
        
        ws_torre.merge_cells(f"A{segunda_tabla_torres_titulo_fila}:M{segunda_tabla_torres_titulo_fila}")
        cell = ws_torre.cell(row=segunda_tabla_torres_titulo_fila, column=1)
        cell.value = "RESUMEN DE PRODUCTIVIDAD POR TORRE CLIENTE"
        cell.font = Font(size=16, bold=True)
        cell.alignment = Alignment(horizontal="center")
        cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        
        fecha_row_torres = segunda_tabla_torres_titulo_fila + 2  # Una fila vacía después del título
        subtitulo_row_torres = segunda_tabla_torres_titulo_fila + 3  # Una fila vacía después del título
        
        # Añadir la fecha para la segunda tabla de torres
        ws_torre.cell(row=fecha_row_torres, column=1, value="Fecha inicial de filtrado:")
        ws_torre.cell(row=fecha_row_torres, column=1).font = Font(size=12, bold=True)
        ws_torre.cell(row=fecha_row_torres, column=2, value=fecha_inicio_str)

        ws_torre.cell(row=subtitulo_row_torres, column=1, value="Fecha final de filtrado:")
        ws_torre.cell(row=subtitulo_row_torres, column=1).font = Font(size=12, bold=True)
        ws_torre.cell(row=subtitulo_row_torres, column=2, value=fecha_fin_str)

        empty_row_torres = subtitulo_row_torres + 1
        
        # Insertar el logo para la segunda tabla de torres
        if os.path.exists(logo_path):
            img4 = XLImage(logo_path)
            img4.height = 35
            img4.width = 140
            ws_torre.add_image(img4, f"M{fecha_row_torres}")  # Logo alineado a la derecha

        # Encabezados para la segunda tabla por torre (sin "Recuento de Fallas")
        headers_torre_cliente = [
            "ID Ciclo",
            "Producto",
            "Torre",
            "Niveles Desmoldados",
            "Niveles Seleccionados",
            "Peso Desmoldado [kg]",
            "Tipo de Fin",
            "Cinta de Desmolde",
            "Inicio [AAAA-MM-DD HH:MM:SS]",
            "Fin [AAAA-MM-DD HH:MM:SS]",
            "Tiempo Desmolde [MM:SS]",
            "Tiempo Pausado [MM:SS]",
            "Tiempo Útil [MM:SS]"
        ]
        
        # Añadir los encabezados de la segunda tabla (después de la fecha)
        headers_row_torres = empty_row_torres + 1  # Una fila vacía después de la fecha/logo
        
        # Agregar encabezados
        for col, header in enumerate(headers_torre_cliente, 1):
            ws_torre.cell(row=headers_row_torres, column=col, value=header)
                
        # Guardar la fila donde empiezan los encabezados para la definición de la segunda tabla
        second_torre_table_first_row = headers_row_torres
        
        # Añadir los mismos datos de la primera tabla pero sin la columna "Recuento de Fallas"
        if detalles_ciclos:
            for ciclo in detalles_ciclos:
                # Formatear fechas
                fecha_inicio = ciclo[8].strftime("%Y-%m-%d %H:%M:%S") if ciclo[8] else "N/A"
                fecha_fin = ciclo[9].strftime("%Y-%m-%d %H:%M:%S") if ciclo[9] else "N/A"
                
                # Obtener tiempos directamente de la base
                tiempo_pausado_str = ciclo[10] or "00:00"
                tiempo_desmolde_str = ciclo[11] or "00:00"
                
                # Convertir a formato MM:SS
                tiempo_pausado_mm_ss = tiempo_a_mm_ss(tiempo_pausado_str)
                tiempo_desmolde_mm_ss = tiempo_a_mm_ss(tiempo_desmolde_str)
                tiempo_util_mm_ss = calcular_tiempo_util_mm_ss(tiempo_desmolde_str, tiempo_pausado_str)
                
                # Obtener tipo de fin
                tipo_fin = ciclo[6] or "N/A"
                
                ws_torre.append([
                    ciclo[0],                  # ID Ciclo
                    ciclo[1] or "DESCONOCIDO", # Producto
                    ciclo[2] or "N/A",         # Torre
                    ciclo[3] or 0,             # Niveles Desmoldados
                    ciclo[4] or 0,             # Niveles Seleccionados
                    f"{ciclo[5]} kg" if ciclo[5] else "0.00 kg", # Peso Desmoldado
                    tipo_fin,                  # Tipo de Fin
                    ciclo[7] or "N/A",         # Cinta de Desmolde
                    fecha_inicio,              # Inicio
                    fecha_fin,                 # Fin
                    tiempo_desmolde_mm_ss,     # Tiempo Desmolde [MM:SS]
                    tiempo_pausado_mm_ss,      # Tiempo Pausado [MM:SS]
                    tiempo_util_mm_ss          # Tiempo Útil [MM:SS]
                    # NO incluir "Recuento de Fallas"
                ])
        else:
            # Si no hay datos, agregar una fila con "Sin datos"
            ws_torre.append([
                "Sin datos",    # ID Ciclo
                "DESCONOCIDO",  # Producto
                "N/A",          # Torre
                0,              # Niveles Desmoldados
                0,              # Niveles Seleccionados
                "0.00 kg",      # Peso Desmoldado
                "N/A",          # Tipo de Fin
                "N/A",          # Cinta de Desmolde
                "N/A",          # Inicio
                "N/A",          # Fin
                "00:00",        # Tiempo Desmolde [MM:SS]
                "00:00",        # Tiempo Pausado [MM:SS]
                "00:00"         # Tiempo Útil [MM:SS]
                # NO incluir "Recuento de Fallas"
            ])
        
        # Crear la segunda tabla de torre
        second_torre_table_last_row = ws_torre.max_row  # La última fila de datos
        
        # Agregar la segunda tabla de torre
        second_torre_table = Table(displayName="ResumenProductividadTorreCliente", ref=f"A{second_torre_table_first_row}:M{second_torre_table_last_row}")
        second_torre_style = TableStyleInfo(
            name="TableStyleMedium9", showFirstColumn=False,
            showLastColumn=False, showRowStripes=True, showColumnStripes=False
        )
        second_torre_table.tableStyleInfo = second_torre_style
        ws_torre.add_table(second_torre_table)
        
        # Ajustar ancho de columnas para ambas hojas
        for sheet in [ws, ws_torre]:
            for col in sheet.columns:
                max_length = 0
                column = None
                for cell in col:
                    # Ignorar las primeras 4 filas (título, espacio, fecha, espacio)
                    if cell.row <= 4:
                        continue
                        
                    if hasattr(cell, "column_letter"):
                        column = cell.column_letter
                    else:
                        continue
                    try:
                        if cell.value:
                            # Calcular el largo del contenido de la celda
                            cell_length = len(str(cell.value))
                            max_length = max(max_length, cell_length)
                    except:
                        pass
                
                if column:
                    # Para encabezados, también revisar la primera fila de datos (que contiene los headers)
                    header_row_found = False
                    for cell in sheet[column]:
                        if cell.row > 4 and cell.value and not header_row_found:
                            # Esta debería ser la fila de encabezados
                            if isinstance(cell.value, str) and ("[" in cell.value or "ID" in cell.value or "Producto" in cell.value):
                                header_length = len(str(cell.value))
                                max_length = max(max_length, header_length)
                                header_row_found = True
                                break
                    
                    # Establecer ancho fijo para la primera columna de la hoja de Torres
                    if sheet == ws_torre and column == "A":
                        final_width = 34.29
                    else:
                        # Establecer un ancho mínimo de 12 y máximo de 35 caracteres para el resto
                        final_width = min(max(max_length + 3, 12), 35)
                    
                    sheet.column_dimensions[column].width = final_width

        wb.save(file_path)
        logger.info(f"Archivo Excel generado en: {file_path}")
        return True  # Retornar True indicando que se generó el Excel exitosamente
    except Exception as e:
        logger.error(f"Error exportando a Excel: {e}")
        raise