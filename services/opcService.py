from opcua import Client
from sqlalchemy.orm import Session
from config.db import get_db
from opcua import ua
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from models.cicloDesmoldeo import CicloDesmoldeo
from models.alarma import Alarma
from models.alarmaHistorico import HistoricoAlarma
from models.recetarioXCiclo import RecetarioXCiclo
from models.torre import Torre
from models.torreconfiguraciones import TorreConfiguraciones
from models.contrasPlc import ContrasPLC
from models.recetario import Recetario

from config.logger_config import logger

from datetime import datetime

import logging
import re
import threading
import time
import asyncio
import json
import os

db_session = next(get_db())
logger = logging.getLogger("uvicorn")
estado_anterior_id_contra = None
LOGS_ALARMA_CICLO = []
ESTADO_CICLO_DESMOLDEO = None
TIEMPO_TRANSCURRIDO = 0
RECETA_ACTUAL = {}
LISTA_DATOS_CICLO = {}
CONTADOR_CICLO_PAUSADO = 0
ultimo_tiempo_check = datetime.now()
lista_resumen_general = {
    "idRecetaActual": 0,
    "idRecetaProxima": 0,
    "CodigoProducto": 0,
    "TotalNiveles": 0,
    "TipoMolde": 0,
    "estadoMaquina": 0,
    "desmoldeoBanda": 0,
    "PesoProducto": 0,
    "TiempoTranscurrido": 0,
    "sdda_nivel_actual": 0,
    "NGripperActual": 0,
    "PesoActualDesmoldado": 0,
    "TorreActual": 0
}
lista_sector_io = {
    "banda_desmoldeo": "",       # string vacío
    "estado_ciclo": False        # valor booleano, por ejemplo False
}
PANTALLA_ENCENDIDA = False
ULTIMO_ESTADO_PANTALLA = None

ciclo_actual = None
NIVELES_SELECCIONADOS_CICLO = 0

ulEstado = None
tiempoCiclo = "00:00 mm:ss"
fechaInicioCIclo = 0

ultimo_estado = None 
ciclo_guardado = None
ULTIMO_NIVEL = None
flag_nivel = 0
PESO_ACTUAL_DESMOLDADO = None
PESO_TOTAL_CICLO = 0

CONTADOR_NIVELES_DESMOLDADOS = 0
ultimo_estado_nivel_desmoldado = False

error = "Error al obtener dato"
banda_desmolde = {
    1:"CINTA A",
    2:"CINTA B"
}
estado_maquina = {
    1: "CICLO INACTIVO",
    2: "CICLO ACTIVO",
    3: "CICLO PAUSADO",
    4: "FINALIZADO",
    5: "CANCELADO"
}
ciclo_tipo_fin = {
    1:"CICLO CORRECTO",
    2:"CICLO CANCELADO"
}
tipo_molde = {
    1: "Molde A",
    2: "Molde B",
    3: "Molde C"
}

INDICE_OPC = os.getenv("INDICE_OPC_UA")

def actualizarContadorCicloPausado(estadoActual):
    global CONTADOR_CICLO_PAUSADO, ultimo_tiempo_check
    
    if not hasattr(actualizarContadorCicloPausado, 'estado_anterior'):
        actualizarContadorCicloPausado.estado_anterior = None
    
    ahora = datetime.now()
    
    if estadoActual == 3:
        delta_segundos = (ahora - ultimo_tiempo_check).total_seconds()
        CONTADOR_CICLO_PAUSADO += delta_segundos
        ultimo_tiempo_check = ahora
        logger.info(f"Contador ciclo pausado: {CONTADOR_CICLO_PAUSADO:.2f} segundos")
    else:
        ultimo_tiempo_check = ahora
        if actualizarContadorCicloPausado.estado_anterior == 3:
            logger.info(f"Ciclo reanudado. Tiempo acumulado en pausa: {CONTADOR_CICLO_PAUSADO:.2f} segundos")
    
    actualizarContadorCicloPausado.estado_anterior = estadoActual
    
    return CONTADOR_CICLO_PAUSADO

def obtenerTiempo(estadoCiclo):
    global tiempoCiclo, fechaInicioCIclo, ulEstado

    if estadoCiclo != ulEstado:
        if estadoCiclo:

            fechaInicioCIclo = datetime.now()
            ulEstado = estadoCiclo
    elif estadoCiclo:
        transcurrido = datetime.now() - fechaInicioCIclo
        transcurrido = datetime.now() - fechaInicioCIclo
        minutos = transcurrido.seconds // 60
        segundos = transcurrido.seconds % 60
        tiempoCiclo = f"{minutos:02}:{segundos:02} mm:ss"
        
    if estadoCiclo == False:
        tiempoCiclo = 0
        fechaInicioCIclo = 0
        ulEstado = None
    #opc_logger.info(f"ULTIMO ESTADO CICLO TT: {ulEstado}")

    return tiempoCiclo

def get_ultimo_ciclo(db):
        try:
            ultimo_ciclo = db.query(CicloDesmoldeo).order_by(CicloDesmoldeo.id.desc()).first()
            if not ultimo_ciclo:
                logger.error(f"No existen datos en la tabla Ciclo")
                return None
            return ultimo_ciclo.id
        except Exception as e:
            logger.error(f"No hay datos en la BDD-CICLO")

def formato_tiempo_mmss(segundos_totales):
    """Convierte segundos totales en formato 'MM:SS'"""
    if segundos_totales is None:
        return "00:00"
    
    minutos = int(segundos_totales // 60)
    segundos = int(segundos_totales % 60)
    return f"{minutos:02d}:{segundos:02d}"

class CustomFormatter(logging.Formatter):
    # Colores ANSI
    orange_bg = "\x1b[48;5;208m"  # Fondo naranja
    white_fg = "\x1b[97;1m"         # Texto blanco
    reset = "\x1b[0m"
    format = "%(levelname)s [CICLOS BASE] %(message)s"

    FORMATS = {
        logging.DEBUG: orange_bg + white_fg + format + reset,
        logging.INFO: orange_bg + white_fg + format + reset,
        logging.WARNING: orange_bg + white_fg + format + reset,
        logging.ERROR: orange_bg + white_fg + format + reset,
        logging.CRITICAL: orange_bg + white_fg + format + reset
    }

    def format(self, record):
        padding = "     "
        colored_prefix = f"{padding}{self.orange_bg}{self.white_fg}{record.levelname} [CICLOS BASE]{self.reset}"
        return f"{colored_prefix} {record.getMessage()}"

# Crear logger personalizado
opc_logger = logging.getLogger("opc_plc")
opc_logger.setLevel(logging.INFO)

# Crear handler para la consola
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(CustomFormatter())
opc_logger.addHandler(ch)

class ObtenerNodosOpc:
    def __init__(self, conexion_servidor):
        self.conexion_servidor = conexion_servidor
    
    def get_node_value_safely(self, parent_node, node_name, default_value=None):
        try:
            child_node = parent_node.get_child([f"{INDICE_OPC}:{node_name}"])
            if child_node:
                return child_node.get_value()
            logger.warning(f"Nodo '{node_name}' no encontrado, usando valor por defecto: {default_value}")
            return default_value
        except Exception as e:
            logger.warning(f"Error al acceder al nodo '{node_name}': {e}")
            return default_value

    async def conexionOpcPLC(self):
        listaRespuesta = []

        global ESTADO_CICLO_DESMOLDEO, LISTA_DATOS_CICLO, ciclo_actual
        global LOGS_ALARMA_CICLO, INDICE_OPC
        global TIEMPO_TRANSCURRIDO, flag_nivel
        global RECETA_ACTUAL, lista_resumen_general, lista_sector_io, PESO_TOTAL_CICLO
        global ultimo_estado, ciclo_guardado, ULTIMO_NIVEL, PESO_ACTUAL_DESMOLDADO
        global CONTADOR_NIVELES_DESMOLDADOS, ultimo_estado_nivel_desmoldado
        global CONTADOR_CICLO_PAUSADO, ultimo_tiempo_check
        global NIVELES_SELECCIONADOS_CICLO

        ciclo_guardado_por_flanco = False
        
        if not hasattr(self, 'ciclo_iniciado_anterior'):
            self.ciclo_iniciado_anterior = False
        if not hasattr(self, 'fin_cancelado_anterior'):
            self.fin_cancelado_anterior = False

        try:
            root_node = await self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["2:ServerInterfaces"])

            
            server_interface_1 = server_interface_node.get_child([f"2:Server interface_1"])

            if not server_interface_1:
                logger.error("No se encontró el nodo 'Server interface_1'.")
                return None

            datos_opc_a_enviar = server_interface_1.get_child([f"{INDICE_OPC}:DATOS OPC A ENVIAR"])
            
            estado_equipo = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:Estado_equipo"])
            e_sdda = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:datosSdda"])
            e_datosRobot = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:datosRobot"])
            e_datosGripper = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:datosGripper"])
            e_desmoldeo = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:desmoldeo"])
            e_datosSeleccionado = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:datosSeleccionados"])
            
            ciclo_iniciado_actual = self.get_node_value_safely(estado_equipo, "Ciclo_iniciado", False)
            fin_cancelado = self.get_node_value_safely(estado_equipo, "finCancelado", False)
            
            flanco_fin_cancelado = fin_cancelado and not self.fin_cancelado_anterior
            niveles_seleccionados = self.get_node_value_safely(e_datosSeleccionado, "nivelesSeleccionados", 0)
            
            # REORDENAMIENTO: Primero detectamos el flanco de niveles desmoldados e incrementamos el contador
            niveles_desmoldados_bool = self.get_node_value_safely(estado_equipo, "nivelesDesmoldados", False)
            if niveles_desmoldados_bool == True and ultimo_estado_nivel_desmoldado == False:
                if ciclo_actual is not None:
                    # Si ya hay un ciclo activo, incrementar el contador
                    CONTADOR_NIVELES_DESMOLDADOS += 1
                    opc_logger.info(f"[NIVEL DESMOLDADO] Se detectó flanco de nivel desmoldado #{CONTADOR_NIVELES_DESMOLDADOS}")
                    
                    if RECETA_ACTUAL:
                        PESO_FILA_PRODUCTO = RECETA_ACTUAL.get("PESO DEL PRODUCTO", 0) * (RECETA_ACTUAL.get("MOLDES POR NIVEL", 0) * RECETA_ACTUAL.get("PRODUCTOS POR MOLDE", 0))
                        PESO_ACTUAL_DESMOLDADO = PESO_FILA_PRODUCTO * CONTADOR_NIVELES_DESMOLDADOS
                        PESO_TOTAL_CICLO = PESO_ACTUAL_DESMOLDADO
                        #opc_logger.info(f"[PESO] Actualizado por nivel desmoldado: {PESO_ACTUAL_DESMOLDADO} kg")
                else:
                    # NUEVA FUNCIONALIDAD: Si no hay ciclo activo, crear uno automáticamente
                    opc_logger.info("[NIVEL DESMOLDADO SIN CICLO] Se detectó flanco de nivel desmoldado sin ciclo activo, creando nuevo ciclo")
                    
                    # Inicializar contadores y variables para el nuevo ciclo
                    CONTADOR_CICLO_PAUSADO = 0
                    CONTADOR_NIVELES_DESMOLDADOS = 1  # Comenzamos en 1 porque ya se está desmoldando el primer nivel
                    ultimo_tiempo_check = datetime.now()
                    ESTADO_CICLO_DESMOLDEO = True
                    ciclo_guardado_por_flanco = False
                    
                    # Obtener información de la receta actual
                    id_receta = self.get_node_value_safely(e_datosSeleccionado, "N_receta_actual", 1)
                    niveles_seleccionados_opc = self.get_node_value_safely(e_datosSeleccionado, "nivelesSeleccionados", 0)
                    
                    # Cargar datos de la receta para validar cantidadNiveles
                    receta_db = db_session.query(Recetario).filter(Recetario.id == id_receta).first()
                    
                    # Validar que nivelesSeleccionados no sea mayor que cantidadNiveles de la receta
                    if receta_db and receta_db.cantidadNiveles:
                        NIVELES_SELECCIONADOS_CICLO = min(niveles_seleccionados_opc, receta_db.cantidadNiveles)
                        if niveles_seleccionados_opc > receta_db.cantidadNiveles:
                            opc_logger.warning(f"[VALIDACIÓN] Niveles seleccionados del OPC ({niveles_seleccionados_opc}) mayor que cantidadNiveles de la receta ({receta_db.cantidadNiveles}). Usando valor máximo permitido: {NIVELES_SELECCIONADOS_CICLO}")
                        else:
                            opc_logger.info(f"[VALIDACIÓN] Niveles seleccionados validados: {NIVELES_SELECCIONADOS_CICLO}")
                    else:
                        NIVELES_SELECCIONADOS_CICLO = niveles_seleccionados_opc
                        opc_logger.warning(f"[VALIDACIÓN] No se pudo validar niveles seleccionados (receta no encontrada o sin cantidadNiveles). Usando valor del OPC: {NIVELES_SELECCIONADOS_CICLO}")
                    
                    opc_logger.info(f"[NIVEL DESMOLDADO SIN CICLO] Usando receta ID: {id_receta}, Niveles seleccionados: {NIVELES_SELECCIONADOS_CICLO}")
                    RECETA_ACTUAL.clear()
                    
                    if receta_db:
                        RECETA_ACTUAL["NOMBRE"] = receta_db.codigoProducto
                        RECETA_ACTUAL["NUMERO DE GRIPPER"] = receta_db.nroGripper
                        RECETA_ACTUAL["TIPO DE MOLDE"] = receta_db.tipoMolde
                        RECETA_ACTUAL["ANCHO PRODUCTO"] = receta_db.anchoProducto
                        RECETA_ACTUAL["ALTO DE PRODUCTO"] = receta_db.altoProducto
                        RECETA_ACTUAL["LARGO DE PRODUCTO"] = receta_db.largoProducto
                        RECETA_ACTUAL["PESO DEL PRODUCTO"] = receta_db.pesoProducto
                        RECETA_ACTUAL["MOLDES POR NIVEL"] = receta_db.moldesNivel
                        RECETA_ACTUAL["ALTO DE MOLDE"] = receta_db.altoMolde
                        RECETA_ACTUAL["LARGO DE MOLDE"] = receta_db.largoMolde
                        RECETA_ACTUAL["ALTURA AJUSTE"] = receta_db.ajusteAltura
                        RECETA_ACTUAL["CANTIDAD NIVELES"] = receta_db.cantidadNiveles
                        RECETA_ACTUAL["DELTA ENTRE NIVELES"] = receta_db.deltaNiveles
                        RECETA_ACTUAL["ALTURA N1"] = receta_db.n1Altura
                        RECETA_ACTUAL["ALTURA DE BASTIDOR"] = receta_db.bastidorAltura
                        RECETA_ACTUAL["ALTURA AJUSTE N1"] = receta_db.ajusteN1Altura
                        RECETA_ACTUAL["PRODUCTOS POR MOLDE"] = receta_db.productosMolde
                        
                        #for key, value in RECETA_ACTUAL.items():
                            #opc_logger.info(f"--------------- Receta actual: {key} = {value}")
                        
                        try:
                            # Crear nuevo ciclo en la base de datos
                            ciclo_desmoldeo = CicloDesmoldeo(
                                fecha_inicio= datetime.now(),
                                fecha_fin=None,
                                estadoMaquina= estado_maquina.get(self.get_node_value_safely(estado_equipo, "Estado_actual", 1), error),
                                bandaDesmolde= banda_desmolde.get(self.get_node_value_safely(e_desmoldeo, "desmoldeobanda", 1), error),
                                tiempoDesmolde=0.0,
                                tiempoPausado=0.0,
                                pesoDesmoldado = 0,
                                id_etapa= 1,
                                id_torre= self.get_node_value_safely(e_datosSeleccionado, "N_torre_actual", 1)
                            )
                            
                            db_session.add(ciclo_desmoldeo)
                            db_session.commit()
                            db_session.refresh(ciclo_desmoldeo)
                            
                            # Calcular el peso por nivel
                            PESO_FILA_PRODUCTO = RECETA_ACTUAL.get("PESO DEL PRODUCTO", 0) * (RECETA_ACTUAL.get("MOLDES POR NIVEL", 0) * RECETA_ACTUAL.get("PRODUCTOS POR MOLDE", 0))
                            PESO_ACTUAL_DESMOLDADO = PESO_FILA_PRODUCTO * CONTADOR_NIVELES_DESMOLDADOS
                            PESO_TOTAL_CICLO = PESO_ACTUAL_DESMOLDADO
                            
                            # Crear registro en RecetarioXCiclo
                            db_recetaXCiclo = RecetarioXCiclo(
                                cantidadNivelesFinalizado = 1,  # Ya se desmoldó un nivel
                                cantidadNivelesSeleccionados = NIVELES_SELECCIONADOS_CICLO,
                                pesoPorNivel = PESO_FILA_PRODUCTO,
                                id_recetario = id_receta,
                                id_ciclo_desmoldeo = ciclo_desmoldeo.id
                            )
                            
                            db_session.add(db_recetaXCiclo)
                            db_session.commit()
                            
                            # Establecer el ciclo actual
                            ciclo_actual = ciclo_desmoldeo
                            opc_logger.info(f"[NIVEL DESMOLDADO SIN CICLO] Nuevo ciclo creado con ID: {ciclo_desmoldeo.id}, nivel inicial: 1, peso calculado: {PESO_ACTUAL_DESMOLDADO} kg")
                            
                        except Exception as e:
                            db_session.rollback()
                            opc_logger.error(f"[ERROR NIVEL DESMOLDADO SIN CICLO] Error al crear nuevo ciclo: {e}")
                    else:
                        opc_logger.error(f"[NIVEL DESMOLDADO SIN CICLO] No se encontró la receta con ID {id_receta} en la base de datos")

            ultimo_estado_nivel_desmoldado = niveles_desmoldados_bool
            
            # AHORA DESPUÉS DEL INCREMENTO verificamos si se ha alcanzado o superado el número de niveles seleccionados
            if ciclo_actual is not None and not ciclo_guardado_por_flanco:
                # Obtener cantidadNivelesSeleccionados de la base de datos para el ciclo actual
                recetario_ciclo = db_session.query(RecetarioXCiclo).filter(RecetarioXCiclo.id_ciclo_desmoldeo == ciclo_actual.id).first()
                
                if recetario_ciclo:
                    niveles_seleccionados_db = recetario_ciclo.cantidadNivelesSeleccionados
                    opc_logger.info(f"[VERIFICACIÓN] Niveles Seleccionados para el ciclo {ciclo_actual.id}: {niveles_seleccionados_db}")
                    
                    if CONTADOR_NIVELES_DESMOLDADOS == niveles_seleccionados_db:
                        opc_logger.info(f"[CICLO COMPLETADO] Niveles desmoldados ({CONTADOR_NIVELES_DESMOLDADOS}) alcanzaron los niveles seleccionados ({niveles_seleccionados_db})")
                        
                        try:
                            ciclo_actualizar = db_session.query(CicloDesmoldeo).filter(CicloDesmoldeo.id == ciclo_actual.id).first()
                            if ciclo_actualizar:
                                id_receta = self.get_node_value_safely(e_datosSeleccionado, "N_receta_actual", 1)
                                if id_receta <= 0:
                                    opc_logger.warning(f"ID de receta inválido: {id_receta}, usando valor predeterminado 1")
                                    id_receta = 1
                                
                                PESO_FILA_PRODUCTO = RECETA_ACTUAL.get("PESO DEL PRODUCTO", 0) * (RECETA_ACTUAL.get("MOLDES POR NIVEL", 0) * RECETA_ACTUAL.get("PRODUCTOS POR MOLDE", 0))
                                peso_calculado = PESO_FILA_PRODUCTO * CONTADOR_NIVELES_DESMOLDADOS
                                
                                # Actualizar cantidadNivelesFinalizado
                                recetario_ciclo.cantidadNivelesFinalizado = CONTADOR_NIVELES_DESMOLDADOS
                                db_session.commit()
                                
                                ciclo_actualizar.fecha_fin = datetime.now()
                                ciclo_actualizar.pesoDesmoldado = peso_calculado
                                
                                tiempo_desmolde_segundos = (datetime.now() - ciclo_actualizar.fecha_inicio).total_seconds()
                                tiempo_pausado_segundos = CONTADOR_CICLO_PAUSADO
                                
                                ciclo_actualizar.tiempoDesmolde = formato_tiempo_mmss(tiempo_desmolde_segundos)
                                ciclo_actualizar.tiempoPausado = formato_tiempo_mmss(tiempo_pausado_segundos)
                                ciclo_actualizar.estadoMaquina = "FINALIZADO"
                                
                                db_session.commit()
                                ciclo_guardado_por_flanco = True
                                opc_logger.info(f"[CICLO COMPLETADO] Ciclo {ciclo_actualizar.id} marcado como FINALIZADO, Peso guardado: {ciclo_actualizar.pesoDesmoldado} kg")
                                
                                ciclo_actual = None
                                ESTADO_CICLO_DESMOLDEO = False
                            else:
                                opc_logger.error(f"[CICLO COMPLETADO] No se encontró ciclo con ID {ciclo_actual.id} para finalizar")
                        except Exception as e:
                            db_session.rollback()
                            opc_logger.error(f"[ERROR CICLO COMPLETADO] Error al finalizar ciclo: {e}")
                else:
                    opc_logger.error(f"[ERROR] No se encontró registro RecetarioXCiclo para el ciclo {ciclo_actual.id}")
            
            # Procesamiento de cancelación manual
            if flanco_fin_cancelado and ciclo_actual is not None and not ciclo_guardado_por_flanco:
                opc_logger.info(f"[CANCELACIÓN MANUAL] Se detectó cancelación manual del ciclo")
                
                try:
                    ciclo_actualizar = db_session.query(CicloDesmoldeo).filter(CicloDesmoldeo.id == ciclo_actual.id).first()
                    if ciclo_actualizar:
                        id_receta = self.get_node_value_safely(e_datosSeleccionado, "N_receta_actual", 1)
                        if id_receta <= 0:
                            opc_logger.warning(f"ID de receta inválido: {id_receta}, usando valor predeterminado 1")
                            id_receta = 1
                        
                        PESO_FILA_PRODUCTO = RECETA_ACTUAL.get("PESO DEL PRODUCTO", 0) * (RECETA_ACTUAL.get("MOLDES POR NIVEL", 0) * RECETA_ACTUAL.get("PRODUCTOS POR MOLDE", 0))
                        peso_calculado = PESO_FILA_PRODUCTO * CONTADOR_NIVELES_DESMOLDADOS
                        
                        # MODIFICACIÓN: Actualizar el registro existente en RecetarioXCiclo
                        receta_ciclo = db_session.query(RecetarioXCiclo).filter(RecetarioXCiclo.id_ciclo_desmoldeo == ciclo_actual.id).first()
                        if receta_ciclo:
                            # Actualizar solo el campo cantidadNivelesFinalizado
                            receta_ciclo.cantidadNivelesFinalizado = CONTADOR_NIVELES_DESMOLDADOS
                        else:
                            # Si por alguna razón no existe, crearlo (caso de respaldo)
                            opc_logger.warning(f"[CANCELACIÓN MANUAL] No se encontró RecetaXCiclo para ciclo {ciclo_actual.id}, creando nuevo registro")
                            db_recetaXCiclo = RecetarioXCiclo(
                                cantidadNivelesFinalizado = CONTADOR_NIVELES_DESMOLDADOS,
                                cantidadNivelesSeleccionados = NIVELES_SELECCIONADOS_CICLO,
                                pesoPorNivel = PESO_FILA_PRODUCTO,
                                id_recetario = id_receta,
                                id_ciclo_desmoldeo = ciclo_actualizar.id
                            )
                            db_session.add(db_recetaXCiclo)
                        
                        db_session.commit()
                        
                        ciclo_actualizar.fecha_fin = datetime.now()
                        ciclo_actualizar.pesoDesmoldado = peso_calculado
                        
                        tiempo_desmolde_segundos = (datetime.now() - ciclo_actualizar.fecha_inicio).total_seconds()
                        tiempo_pausado_segundos = CONTADOR_CICLO_PAUSADO
                        
                        ciclo_actualizar.tiempoDesmolde = formato_tiempo_mmss(tiempo_desmolde_segundos)
                        ciclo_actualizar.tiempoPausado = formato_tiempo_mmss(tiempo_pausado_segundos)
                        ciclo_actualizar.estadoMaquina = "CANCELADO"
                        
                        db_session.commit()
                        ciclo_guardado_por_flanco = True
                        opc_logger.info(f"[CANCELACIÓN MANUAL] Ciclo {ciclo_actualizar.id} marcado como CANCELADO, Peso guardado: {ciclo_actualizar.pesoDesmoldado} kg")
                        
                        ciclo_actual = None
                        ESTADO_CICLO_DESMOLDEO = False
                    else:
                        opc_logger.error(f"[CANCELACIÓN MANUAL] No se encontró ciclo con ID {ciclo_actual.id} para finalizar")
                except Exception as e:
                    db_session.rollback()
                    opc_logger.error(f"[ERROR CANCELACIÓN MANUAL] Error al finalizar ciclo: {e}")

            listaDatos = estado_equipo.get_children()
            for child in listaDatos:
                browse_name = child.get_browse_name().Name
                value = child.get_value()
                LISTA_DATOS_CICLO[browse_name] = value

            flanco_inicio_ciclo = ciclo_iniciado_actual == True and self.ciclo_iniciado_anterior == False
            
            if flanco_inicio_ciclo:
                opc_logger.info("[FLANCO CICLO_INICIADO] Se detectó inicio de ciclo")

                # Obtener niveles seleccionados del OPC y ID de receta
                niveles_seleccionados_opc = self.get_node_value_safely(e_datosSeleccionado, "nivelesSeleccionados", 0)
                id_receta = self.get_node_value_safely(e_datosSeleccionado, "N_receta_actual", 1)
                
                # Validar niveles seleccionados contra la receta de la base de datos
                receta_validacion = db_session.query(Recetario).filter(Recetario.id == id_receta).first()
                if receta_validacion and receta_validacion.cantidadNiveles:
                    NIVELES_SELECCIONADOS_CICLO = min(niveles_seleccionados_opc, receta_validacion.cantidadNiveles)
                    if niveles_seleccionados_opc > receta_validacion.cantidadNiveles:
                        opc_logger.warning(f"[VALIDACIÓN FLANCO] Niveles seleccionados del OPC ({niveles_seleccionados_opc}) mayor que cantidadNiveles de la receta ({receta_validacion.cantidadNiveles}). Usando valor máximo permitido: {NIVELES_SELECCIONADOS_CICLO}")
                    else:
                        opc_logger.info(f"[VALIDACIÓN FLANCO] Niveles seleccionados validados: {NIVELES_SELECCIONADOS_CICLO}")
                else:
                    NIVELES_SELECCIONADOS_CICLO = niveles_seleccionados_opc
                    opc_logger.warning(f"[VALIDACIÓN FLANCO] No se pudo validar niveles seleccionados (receta no encontrada o sin cantidadNiveles). Usando valor del OPC: {NIVELES_SELECCIONADOS_CICLO}")
                
                opc_logger.info(f"[FLANCO CICLO_INICIADO] Niveles seleccionados: {NIVELES_SELECCIONADOS_CICLO}")

                if ciclo_actual is not None:
                    opc_logger.warning(f"[CICLO SOLAPADO] Se detectó inicio de ciclo mientras otro estaba activo (ID: {ciclo_actual.id})")
                    
                    try:
                        ciclo_actualizar = db_session.query(CicloDesmoldeo).filter(CicloDesmoldeo.id == ciclo_actual.id).first()
                        if ciclo_actualizar:
                            logger.info(f"[CICLO SOLAPADO] Cancelando ciclo anterior ID: {ciclo_actualizar.id}")
                            
                            id_receta = self.get_node_value_safely(e_datosSeleccionado, "N_receta_actual", 1)
                            if id_receta <= 0:
                                id_receta = 1
                            
                            PESO_FILA_PRODUCTO = RECETA_ACTUAL.get("PESO DEL PRODUCTO", 0) * (RECETA_ACTUAL.get("MOLDES POR NIVEL", 0) * RECETA_ACTUAL.get("PRODUCTOS POR MOLDE", 0))
                            
                            peso_calculado = PESO_FILA_PRODUCTO * CONTADOR_NIVELES_DESMOLDADOS
                            logger.info(f"[CICLO SOLAPADO] Recalculando peso: {PESO_FILA_PRODUCTO} kg × {CONTADOR_NIVELES_DESMOLDADOS} niveles = {peso_calculado} kg")
                            
                            # MODIFICACIÓN: Actualizar el registro existente en RecetarioXCiclo
                            receta_ciclo = db_session.query(RecetarioXCiclo).filter(RecetarioXCiclo.id_ciclo_desmoldeo == ciclo_actual.id).first()
                            if receta_ciclo:
                                # Actualizar solo el campo cantidadNivelesFinalizado
                                receta_ciclo.cantidadNivelesFinalizado = CONTADOR_NIVELES_DESMOLDADOS
                                logger.info(f"[CICLO SOLAPADO] RecetaXCiclo actualizado para ciclo {ciclo_actual.id}, niveles finalizados: {CONTADOR_NIVELES_DESMOLDADOS}")
                            else:
                                # Si por alguna razón no existe, crearlo (caso de respaldo)
                                logger.warning(f"[CICLO SOLAPADO] No se encontró RecetaXCiclo para ciclo {ciclo_actual.id}, creando nuevo registro")
                                db_recetaXCiclo = RecetarioXCiclo(
                                    cantidadNivelesFinalizado = CONTADOR_NIVELES_DESMOLDADOS,
                                    cantidadNivelesSeleccionados = NIVELES_SELECCIONADOS_CICLO,
                                    pesoPorNivel = PESO_FILA_PRODUCTO,
                                    id_recetario = id_receta,
                                    id_ciclo_desmoldeo = ciclo_actualizar.id
                                )
                                db_session.add(db_recetaXCiclo)
                            
                            db_session.commit()
                            
                            ciclo_actualizar.fecha_fin = datetime.now()
                            ciclo_actualizar.pesoDesmoldado = peso_calculado
                            
                            tiempo_desmolde_segundos = (datetime.now() - ciclo_actualizar.fecha_inicio).total_seconds()
                            tiempo_pausado_segundos = CONTADOR_CICLO_PAUSADO
                            
                            ciclo_actualizar.tiempoDesmolde = formato_tiempo_mmss(tiempo_desmolde_segundos)
                            ciclo_actualizar.tiempoPausado = formato_tiempo_mmss(tiempo_pausado_segundos)
                            ciclo_actualizar.estadoMaquina = "CANCELADO"
                            
                            db_session.commit()
                            opc_logger.info(f"[CICLO SOLAPADO] Ciclo anterior {ciclo_actualizar.id} marcado como CANCELADO con éxito")
                        else:
                            opc_logger.error(f"[CICLO SOLAPADO] No se pudo encontrar el ciclo con ID {ciclo_actual.id} para cancelar")
                    except Exception as e:
                        db_session.rollback()
                        opc_logger.error(f"[ERROR CICLO SOLAPADO] Error al cancelar ciclo anterior: {e}")
                
                CONTADOR_CICLO_PAUSADO = 0
                CONTADOR_NIVELES_DESMOLDADOS = 0
                ultimo_tiempo_check = datetime.now()
                ESTADO_CICLO_DESMOLDEO = True
                ciclo_guardado_por_flanco = False

                # Obtener receta antes de crear el ciclo para usar los datos validados
                receta_db = db_session.query(Recetario).filter(Recetario.id == id_receta).first()
                
                RECETA_ACTUAL.clear()
                if receta_db:
                    RECETA_ACTUAL["NOMBRE"] = receta_db.codigoProducto
                    RECETA_ACTUAL["NUMERO DE GRIPPER"] = receta_db.nroGripper
                    RECETA_ACTUAL["TIPO DE MOLDE"] = receta_db.tipoMolde
                    RECETA_ACTUAL["ANCHO PRODUCTO"] = receta_db.anchoProducto
                    RECETA_ACTUAL["ALTO DE PRODUCTO"] = receta_db.altoProducto
                    RECETA_ACTUAL["LARGO DE PRODUCTO"] = receta_db.largoProducto
                    RECETA_ACTUAL["PESO DEL PRODUCTO"] = receta_db.pesoProducto
                    RECETA_ACTUAL["MOLDES POR NIVEL"] = receta_db.moldesNivel
                    RECETA_ACTUAL["ALTO DE MOLDE"] = receta_db.altoMolde
                    RECETA_ACTUAL["LARGO DE MOLDE"] = receta_db.largoMolde
                    RECETA_ACTUAL["ALTURA AJUSTE"] = receta_db.ajusteAltura
                    RECETA_ACTUAL["CANTIDAD NIVELES"] = receta_db.cantidadNiveles
                    RECETA_ACTUAL["DELTA ENTRE NIVELES"] = receta_db.deltaNiveles
                    RECETA_ACTUAL["ALTURA N1"] = receta_db.n1Altura
                    RECETA_ACTUAL["ALTURA DE BASTIDOR"] = receta_db.bastidorAltura
                    RECETA_ACTUAL["ALTURA AJUSTE N1"] = receta_db.ajusteN1Altura
                    RECETA_ACTUAL["PRODUCTOS POR MOLDE"] = receta_db.productosMolde
                    
                    #for key, value in RECETA_ACTUAL.items():
                        #opc_logger.info(f"--------------- Receta actual: {key} = {value}")
                else:
                    opc_logger.error(f"[FLANCO CICLO_INICIADO] No se encontró la receta con ID {id_receta} en la base de datos")
                
                fin_cancelado_verificacion = self.get_node_value_safely(estado_equipo, "finCancelado", False)
                
                ciclo_ya_cancelado = fin_cancelado_verificacion
                
                if ciclo_ya_cancelado:
                    opc_logger.warning("[CICLO CANCELADO DURANTE INICIO] Se detectó cancelación mientras se procesaba el inicio")
                    
                    ciclo_desmoldeo = CicloDesmoldeo(
                        fecha_inicio=datetime.now(),
                        fecha_fin=datetime.now(),
                        estadoMaquina="CANCELADO AL INICIAR",
                        bandaDesmolde=banda_desmolde.get(self.get_node_value_safely(e_desmoldeo, "desmoldeobanda", 1), error),
                        tiempoDesmolde="00:00",
                        tiempoPausado="00:00",
                        pesoDesmoldado=0,
                        id_etapa=1,
                        id_torre=self.get_node_value_safely(e_datosSeleccionado, "N_torre_actual", 1)
                    )
                else:
                    ciclo_desmoldeo = CicloDesmoldeo(
                        fecha_inicio= datetime.now(),
                        fecha_fin=None,
                        estadoMaquina= estado_maquina.get(self.get_node_value_safely(estado_equipo, "Estado_actual", 1), error),
                        bandaDesmolde= banda_desmolde.get(self.get_node_value_safely(e_desmoldeo, "desmoldeobanda", 1), error),
                        tiempoDesmolde=0.0,
                        tiempoPausado=0.0,
                        pesoDesmoldado = 0,
                        id_etapa= 1,
                        id_torre= self.get_node_value_safely(e_datosSeleccionado, "N_torre_actual", 1)
                    )
                try:
                    db_session.add(ciclo_desmoldeo)
                    db_session.commit()
                    db_session.refresh(ciclo_desmoldeo)
                    
                    # MODIFICACIÓN: Crear registro en RecetarioXCiclo al iniciar ciclo
                    PESO_FILA_PRODUCTO = RECETA_ACTUAL.get("PESO DEL PRODUCTO", 0) * (RECETA_ACTUAL.get("MOLDES POR NIVEL", 0) * RECETA_ACTUAL.get("PRODUCTOS POR MOLDE", 0))
                    
                    db_recetaXCiclo = RecetarioXCiclo(
                        cantidadNivelesFinalizado = 0,
                        cantidadNivelesSeleccionados = NIVELES_SELECCIONADOS_CICLO,
                        pesoPorNivel = PESO_FILA_PRODUCTO,
                        id_recetario = id_receta,
                        id_ciclo_desmoldeo = ciclo_desmoldeo.id
                    )
                    db_session.add(db_recetaXCiclo)
                    db_session.commit()
                    #opc_logger.info(f"[NUEVO CICLO] RecetaXCiclo creado para ciclo {ciclo_desmoldeo.id}, niveles seleccionados: {NIVELES_SELECCIONADOS_CICLO}")
                    
                    if ciclo_ya_cancelado:
                        # Si el ciclo ya está cancelado, actualizar inmediatamente RecetaXCiclo
                        receta_ciclo = db_session.query(RecetarioXCiclo).filter(RecetarioXCiclo.id_ciclo_desmoldeo == ciclo_desmoldeo.id).first()
                        if receta_ciclo:
                            receta_ciclo.cantidadNivelesFinalizado = 0  # Se cancela antes de empezar
                            db_session.commit()
                        
                        opc_logger.info(f"[CICLO CANCELADO DURANTE INICIO] Ciclo {ciclo_desmoldeo.id} creado y marcado como CANCELADO AL INICIAR automáticamente")
                        ESTADO_CICLO_DESMOLDEO = False
                        ciclo_actual = None  # No establecer como ciclo actual
                    else:
                        ciclo_actual = ciclo_desmoldeo
                        opc_logger.info(f"[FLANCO CICLO_INICIADO] NUEVO CICLO CREADO: {ciclo_desmoldeo.id}")
                        
                except Exception as e:
                    db_session.rollback()
                    opc_logger.error(f"ERROR AL GUARDAR CICLO-DESM EN BDD: {e}")
            
            # Actualizar estados anteriores para la próxima detección de flancos
            self.ciclo_iniciado_anterior = ciclo_iniciado_actual
            self.fin_cancelado_anterior = fin_cancelado
            
            if ciclo_iniciado_actual is False and ESTADO_CICLO_DESMOLDEO is True:
                if not ciclo_guardado_por_flanco and ciclo_actual is not None:
                    #opc_logger.warning(f"[CICLO NO FINALIZADO] Ciclo_iniciado cambió a FALSE sin finalización para ciclo {ciclo_actual.id}")
                    pass
                ESTADO_CICLO_DESMOLDEO = False
            else:
                ESTADO_CICLO_DESMOLDEO = ciclo_iniciado_actual
            
            if self.get_node_value_safely(e_sdda, "sdda_nivel_actual", 0) > 0:
                ULTIMO_NIVEL = self.get_node_value_safely(e_sdda, "sdda_nivel_actual", 0)
                opc_logger.info(f"VALOR NIVEL ACTUAL: {ULTIMO_NIVEL}")
            
            id_receta_actual = self.get_node_value_safely(e_datosSeleccionado, "N_receta_actual", 1)
            receta_db = db_session.query(Recetario).filter(Recetario.id == id_receta_actual).first()
            
            if receta_db:
                RECETA_ACTUAL.clear()
                RECETA_ACTUAL["NOMBRE"] = receta_db.codigoProducto
                RECETA_ACTUAL["NUMERO DE GRIPPER"] = receta_db.nroGripper
                RECETA_ACTUAL["TIPO DE MOLDE"] = receta_db.tipoMolde
                RECETA_ACTUAL["ANCHO PRODUCTO"] = receta_db.anchoProducto
                RECETA_ACTUAL["ALTO DE PRODUCTO"] = receta_db.altoProducto
                RECETA_ACTUAL["LARGO DE PRODUCTO"] = receta_db.largoProducto
                RECETA_ACTUAL["PESO DEL PRODUCTO"] = receta_db.pesoProducto
                RECETA_ACTUAL["MOLDES POR NIVEL"] = receta_db.moldesNivel
                RECETA_ACTUAL["ALTO DE MOLDE"] = receta_db.altoMolde
                RECETA_ACTUAL["LARGO DE MOLDE"] = receta_db.largoMolde
                RECETA_ACTUAL["ALTURA AJUSTE"] = receta_db.ajusteAltura
                RECETA_ACTUAL["CANTIDAD NIVELES"] = receta_db.cantidadNiveles
                RECETA_ACTUAL["DELTA ENTRE NIVELES"] = receta_db.deltaNiveles
                RECETA_ACTUAL["ALTURA N1"] = receta_db.n1Altura
                RECETA_ACTUAL["ALTURA DE BASTIDOR"] = receta_db.bastidorAltura
                RECETA_ACTUAL["ALTURA AJUSTE N1"] = receta_db.ajusteN1Altura
                RECETA_ACTUAL["PRODUCTOS POR MOLDE"] = receta_db.productosMolde
            
            receta_proximo = db_session.query(Recetario).filter(Recetario.id == self.get_node_value_safely(e_datosSeleccionado, "N_receta_actual", 1)).first()
            
            if not (ESTADO_CICLO_DESMOLDEO == False and ultimo_estado == True):
                lista_resumen_general["idRecetaActual"] = self.get_node_value_safely(e_datosSeleccionado, "N_receta_actual", 0)
                lista_resumen_general["idRecetaProxima"] = receta_proximo.codigoProducto if receta_proximo else ""
                lista_resumen_general["CodigoProducto"] = RECETA_ACTUAL.get("NOMBRE", "")
                lista_resumen_general["TotalNiveles"] = RECETA_ACTUAL.get("CANTIDAD NIVELES", 0)
                
                #CORRECCION PORQUE EL VALOR DE TIPOMOLDE ESTA MAL EN BASE (VARCHAR)
                tipo_molde_valor = RECETA_ACTUAL.get("TIPO DE MOLDE", 0)
                if isinstance(tipo_molde_valor, str):
                    try:
                        tipo_molde_valor = int(tipo_molde_valor)
                    except (ValueError, TypeError):
                        tipo_molde_valor = 0
                elif tipo_molde_valor is None:
                    tipo_molde_valor = 0
                resultado_tipo_molde = tipo_molde.get(tipo_molde_valor, "")
                lista_resumen_general["TipoMolde"] = resultado_tipo_molde

                lista_resumen_general["desmoldeoBanda"] = banda_desmolde.get(self.get_node_value_safely(e_desmoldeo, "desmoldeobanda", 0), error)
                lista_resumen_general["sdda_nivel_actual"] = ULTIMO_NIVEL if ULTIMO_NIVEL else 0
                lista_resumen_general["NGripperActual"] = self.get_node_value_safely(e_datosGripper, "NGripperActual", 0)
                lista_resumen_general["TorreActual"] = self.get_node_value_safely(e_datosSeleccionado, "N_torre_actual", 0)
                
                if ESTADO_CICLO_DESMOLDEO == False:
                    lista_resumen_general["PesoProducto"] = 0.0
                    lista_resumen_general["PesoActualDesmoldado"] = 0.0
                elif RECETA_ACTUAL:
                    PESO_FILA_PRODUCTO = RECETA_ACTUAL.get("PESO DEL PRODUCTO", 0) * (RECETA_ACTUAL.get("MOLDES POR NIVEL", 0) * RECETA_ACTUAL.get("PRODUCTOS POR MOLDE", 0))
                    lista_resumen_general["PesoProducto"] = round(PESO_FILA_PRODUCTO, 2)
                    PESO_ACTUAL_DESMOLDADO = PESO_FILA_PRODUCTO * CONTADOR_NIVELES_DESMOLDADOS
                    PESO_TOTAL_CICLO = PESO_ACTUAL_DESMOLDADO
                    lista_resumen_general["PesoActualDesmoldado"] = round(PESO_TOTAL_CICLO, 2)
                else:
                    lista_resumen_general["PesoProducto"] = 0.0
                    lista_resumen_general["PesoActualDesmoldado"] = 0.0

            if flag_nivel != ULTIMO_NIVEL and ESTADO_CICLO_DESMOLDEO == True:
                flag_nivel = ULTIMO_NIVEL
                if RECETA_ACTUAL:
                    PESO_FILA_PRODUCTO = RECETA_ACTUAL.get("PESO DEL PRODUCTO", 0) * (RECETA_ACTUAL.get("MOLDES POR NIVEL", 0) * RECETA_ACTUAL.get("PRODUCTOS POR MOLDE", 0))
                    PESO_ACTUAL_DESMOLDADO = PESO_FILA_PRODUCTO * CONTADOR_NIVELES_DESMOLDADOS
                    PESO_TOTAL_CICLO = PESO_ACTUAL_DESMOLDADO

            estado_actual_valor = self.get_node_value_safely(estado_equipo, "Estado_actual", 1)
            actualizarContadorCicloPausado(estado_actual_valor)

            if ESTADO_CICLO_DESMOLDEO == False and ultimo_estado == True:
                lista_resumen_general = {
                    "idRecetaActual": 0,
                    "idRecetaProxima": 0,
                    "CodigoProducto": "",
                    "TotalNiveles": 0,
                    "TipoMolde": "",
                    "desmoldeoBanda": "",
                    "PesoProducto": 0.0,
                    "sdda_nivel_actual": 0,
                    "NGripperActual": 0,
                    "PesoActualDesmoldado": 0.0,
                    "TorreActual": 0
                }
                
                PESO_ACTUAL_DESMOLDADO = 0
                PESO_TOTAL_CICLO = 0
                ULTIMO_NIVEL = 0
                CONTADOR_CICLO_PAUSADO = 0
                ciclo_guardado_por_flanco = False
            
            ultimo_estado = ESTADO_CICLO_DESMOLDEO

            tiempo_transcurrido_websocket = "00:00 mm:ss"  # Valor por defecto
            
            if ciclo_actual is not None:
                try:
                    # Obtener el ciclo actual de la base de datos para obtener fecha_inicio
                    ciclo_bd = db_session.query(CicloDesmoldeo).filter(CicloDesmoldeo.id == ciclo_actual.id).first()
                    if ciclo_bd and ciclo_bd.fecha_inicio:
                        # Calcular tiempo transcurrido desde fecha_inicio
                        tiempo_transcurrido_segundos = (datetime.now() - ciclo_bd.fecha_inicio).total_seconds()
                        # Convertir a formato mm:ss
                        minutos = int(tiempo_transcurrido_segundos // 60)
                        segundos = int(tiempo_transcurrido_segundos % 60)
                        tiempo_transcurrido_websocket = f"{minutos:02d}:{segundos:02d} mm:ss"
                except Exception as e:
                    opc_logger.error(f"Error calculando tiempo transcurrido para WebSocket: {e}")
                    tiempo_transcurrido_websocket = "00:00 mm:ss"

            TIEMPO_TRANSCURRIDO = obtenerTiempo(ESTADO_CICLO_DESMOLDEO)
            lista_resumen_general["estadoMaquina"] = estado_maquina.get(estado_actual_valor, error)
            lista_resumen_general["TiempoTranscurrido"] = tiempo_transcurrido_websocket
            listaRespuesta.append(lista_resumen_general)

            lista_sector_io["banda_desmoldeo"] = banda_desmolde.get(self.get_node_value_safely(e_desmoldeo, "desmoldeobanda", 1), error)
            lista_sector_io["estado_ciclo"] = ESTADO_CICLO_DESMOLDEO

            listaCelda, listaDatosGeneral = await asyncio.gather(
                self.obtenerDatosCelda(
                    estado_actual_valor, 
                    self.get_node_value_safely(e_sdda, "sdda_nivel_actual", 0)
                ),
                self.obtenerListaGeneral(e_datosRobot, e_datosGripper, e_desmoldeo, e_datosSeleccionado, e_sdda, lista_sector_io)
            )
            
            listaRespuesta.append(listaCelda)
            listaRespuesta.append(listaDatosGeneral)
            
            with open('alarmas.json', 'r') as file:
                data = json.load(file)
            alarmas = list(data.values())
            alarmas_ordenadas = sorted(alarmas, key=lambda x: not x['estadoAlarma'])
            listaRespuesta.append(alarmas_ordenadas)

            fecha_actual_h = datetime.now()
            una_hora_atras = fecha_actual_h - timedelta(hours=1)

            datos_alarmas_h = (
                db_session.query(Alarma, HistoricoAlarma)
                .join(Alarma, HistoricoAlarma.id_alarma == Alarma.id)
                .filter(HistoricoAlarma.tiempo_inicio.between(una_hora_atras, fecha_actual_h))
                .all()
            )

            registro_historico_a = []

            for alarma, historico_alarma in datos_alarmas_h:
                registro_alarma = {
                    "id_alarma" : alarma.id,
                    "estadoAlarma" : historico_alarma.estadoAlarma,
                    "tipoAlarma" : alarma.tipoAlarma,
                    "descripcion" : alarma.descripcion, 
                    "fechaRegistro" : historico_alarma.tiempo_inicio.isoformat(),
                }
                registro_historico_a.append(registro_alarma)
            
            listaRespuesta.append(registro_historico_a)

            return listaRespuesta
            
        except Exception as e:
            logger.exception(f"Error general en conexionOpcPLC: {e}")
            await self.conexion_servidor.handle_reconnect()
            return None

    async def actualizarRecetas(self):
        global PANTALLA_ENCENDIDA, ULTIMO_ESTADO_PANTALLA, INDICE_OPC
        lista_recetas = {}
        
        try:
            root_node = await self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["2:ServerInterfaces"])


            server_interface_1 = server_interface_node.get_child([f"2:Server interface_1"])

            if not server_interface_1:
                logger.error("No se encontró el nodo 'Server interface_1'.")
                return None

            datos_opc_a_enviar = server_interface_1.get_child([f"{INDICE_OPC}:DATOS OPC A ENVIAR"])
            e_datosSeleccionado = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:datosSeleccionados"])
            e_listaRecetario = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:RECETARIO"])
            pantalla_receta = e_datosSeleccionado.get_child([f"{INDICE_OPC}:pantalla_receta"])
            PANTALLA_ENCENDIDA = pantalla_receta.get_value()
            logger.error(f"PANTALLA OPC: {PANTALLA_ENCENDIDA}")
            

            if PANTALLA_ENCENDIDA != ULTIMO_ESTADO_PANTALLA :
                if PANTALLA_ENCENDIDA == False:

                    try:
                        for child in e_listaRecetario.get_children():
                            if not child:
                                logger.error(f"No se pudo acceder a la redec")
                            receta = {}
                            for elem in child.get_children():
                                receta[elem.get_browse_name().Name ]= elem.get_value()
                            lista_recetas[child.get_browse_name().Name] = receta
                            logger.info(f"Receta {child.get_browse_name().Name} obtenida con {len(receta)} valores.")
                    except Exception as e:
                        logger.error(f"Nose puedo acceder a la estructura de recetario")                            

                    self.guardarRecetaEnBD(lista_recetas)

                
            ULTIMO_ESTADO_PANTALLA = PANTALLA_ENCENDIDA


        except Exception as e:
            logger.error(f"Error al intertar ACTUALIZAR RECETAS {e}")    

    async def obtenerDatosCelda(self, estadoActual, sddaNivelActual):
        resultado = {}
        global TIEMPO_TRANSCURRIDO
        global ESTADO_CICLO_DESMOLDEO
        global RECETA_ACTUAL, INDICE_OPC
        try:

            resultado["Nombre actual"] = RECETA_ACTUAL.get("NOMBRE")

            peso_producto = RECETA_ACTUAL.get("PESO DEL PRODUCTO") or 0
            productos_por_molde = RECETA_ACTUAL.get("PRODUCTOS POR MOLDE") or 0
            resultado["PesoProducto"] = round(peso_producto * productos_por_molde, 2)
            
            resultado["TotalNiveles"] = RECETA_ACTUAL.get("CANTIDAD NIVELES")

            resultado["sdda_nivel_actual"] = sddaNivelActual
            resultado["estadoMaquina"] = estado_maquina.get(estadoActual)
            resultado["iniciado"] = ESTADO_CICLO_DESMOLDEO

            # Asegurarse de que PesoActualDesmoldado sea 0 cuando el ciclo esté inactivo
            if ESTADO_CICLO_DESMOLDEO == False:
                resultado["PesoActualDesmoldado"] = 0.0
            else:
                # Evitar TypeError en caso de valores None
                peso_producto = round(resultado.get("PesoProducto", 0),2)
                nivel_actual = resultado.get("sdda_nivel_actual", 0)
                resultado["PesoActualDesmoldado"] = round((peso_producto or 0) * nivel_actual, 2)
            resultado["TiempoTranscurrido"] = TIEMPO_TRANSCURRIDO

            celda = {
                "Desmoldeo": resultado,
                "Encajonado": [],
                "Palletizado": []
            }
            return celda

        except Exception as e:
            logger.exception("Error al obtener los datos de la celda:")
            return None
        
    async def obtenerListaGeneral(self, datosRobotNODO, datosGripperNODO, desmoldeoNODO, datosSeleccionadoNODO, datosSddaNODO, lista_sector_io):
        global RECETA_ACTUAL, INDICE_OPC
        datosGripper = {}
        datosRobot = {}
        datosDesmoldeo = {}
        datosSeleccionado = {}
        datosSdda = {}
        listaDatos = {}

        try:
            datosRobotOPC = datosRobotNODO.get_children()
            datosGripperOPC = datosGripperNODO.get_children()
            desmoldeoOPC = desmoldeoNODO.get_children()
            datosSeleccionadoOPC = datosSeleccionadoNODO.get_children()
            datosSddaOPC = datosSddaNODO.get_children()

            for child in datosGripperOPC:
                datosGripper[child.get_browse_name().Name] = child.get_value()
            for child in datosRobotOPC:
                datosRobot[child.get_browse_name().Name] = child.get_value()
            for child in desmoldeoOPC:
                datosDesmoldeo[child.get_browse_name().Name] = child.get_value()
            for child in datosSeleccionadoOPC:
                if child.get_browse_name().Name == "N_torre_actual" or child.get_browse_name().Name == "N_torre_proxima":
                    datosSeleccionado[child.get_browse_name().Name] = child.get_value()
            for child in datosSddaOPC:
                datosSdda[child.get_browse_name().Name] = child.get_value()

            datosSeleccionado["TotalNiveles"] = RECETA_ACTUAL.get("CANTIDAD NIVELES")

            listaDatos["datosGripper"] = datosGripper
            listaDatos["datosRobot"] = datosRobot
            listaDatos["datosDesmoldeo"] = datosDesmoldeo
            listaDatos["datosTorre"] = datosSeleccionado
            listaDatos["datosSdda"] = datosSdda
            listaDatos["sector_IO"] = lista_sector_io

            return listaDatos

        except Exception as e:
            logger.error(f"Error al obtener la lista general de datos: {e}")
            return None

    async def ConexionPLCRecetas(self):
        global INDICE_OPC
        lista_datos_seleccionados = {}
        try:
            db: Session = next(get_db())
            root_node = await self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["2:ServerInterfaces"])


            server_interface_1 = server_interface_node.get_child([f"2:Server interface_1"])

            if not server_interface_1:
                logger.error("No se encontró el nodo 'Server interface_1'.")
                return None

            datos_opc_a_enviar = server_interface_1.get_child([f"{INDICE_OPC}:DATOS OPC A ENVIAR"])
            e_datosSeleccionado = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:datosSeleccionados"])

            e_datosTorre = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:datosTorre"])
            nivelesHN_node = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:DatosNivelesHN"])
            nivelesuHN_node = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:DatosNivelesuHN"])
            nivelesChG_node = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:DatosNivelesChG"])
            nivelesChB_node = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:DatosNivelesChB"])
            nivelesFA_node = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:DatosNivelesFA"])

            Comprobacion_datos_node = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:Comprobacion_datos"])

            children = e_datosSeleccionado.get_children()
            for child in children:
                browse_name = child.get_browse_name().Name
                value = child.get_value()
                lista_datos_seleccionados[browse_name] = value
            
            torres = db.query(Torre).filter(Torre.id_recetario == lista_datos_seleccionados.get("N_receta_proxima")).all()

            torresconfiguraciones = db.query(TorreConfiguraciones).all()

            if not torres:
                logger.error("No se encontraron torres para el recetario proporcionado.")
                return {"mensaje": "No se encontraron torres para el recetario proporcionado."}

            if not torresconfiguraciones:
                logger.error("No se encontraron torres para el recetario proporcionado.")
                return {"mensaje": "No se encontraron torres para el recetario proporcionado."}

            try:
                torre_proxima = int(lista_datos_seleccionados.get("N_torre_proxima"))
                primera_torre = torres[0]

                ntorre_comparacion = (int(primera_torre.NTorre) + torre_proxima - 1)
                print(f"Valor de ntorre_comparacion: {ntorre_comparacion}")

                exitosotorres = False

                for torre in torres:
                    try:
                        torre_ntorre = int(torre.NTorre)

                        if torre_ntorre == ntorre_comparacion:
                            print(f"Torre encontrada: ID={torre.id}, NTorre={torre.NTorre}, id_recetario={torre.id_recetario}")
                            
                            datosTorres = {
                                "TAG": torre.id,
                                "id": torre.NTorre,
                                "hBastidor": torre.hBastidor,
                                "hAjuste": torre.hAjuste,
                                "hAjusteN1": torre.hAjusteN1,
                                "DisteNivel": torre.DisteNivel,
                            }
                            
                            print(f"Datos de torre: {datosTorres}")
                            
                            exitosotorres = (
                                await self.escribirDatosTorreOpc(datosTorres, e_datosTorre)
                            )

                    except Exception as e:
                        print(f"Se produjo un error al procesar la torre: {e}")
                        continue  

                        # Crear un diccionario para almacenar los valores por tipo y nivel
                correccionesHN = [0] * 11  # Inicializamos un arreglo de 11 elementos para "HN"
                correccionesFallas = [0] * 11  # Para "Fallas"
                correccionesuHN = [0] * 11  # Para "uHN"
                correccionesChG = [0] * 11  # Para "ChG"
                correccionesChB = [0] * 11  # Para "ChB"

                for torreconfiguraciones in torresconfiguraciones:
                    try:
                        torre_ntorre = int(torreconfiguraciones.id_torreNum)
                        tipo = str(torreconfiguraciones.tipo)
                        nivel = int(torreconfiguraciones.nivel)  # Nivel de la corrección
                        valor = int(torreconfiguraciones.valor)  # Valor para ese nivel

                        if torre_ntorre == ntorre_comparacion:  # Comparamos con la torre correspondiente
                            if tipo == "HN":
                                correccionesHN[nivel - 1] = valor
                            
                            if tipo == "Fallas":
                                correccionesFallas[nivel - 1] = valor
                            
                            if tipo == "uHN":
                                correccionesuHN[nivel - 1] = valor
                            
                            if tipo == "ChG":
                                correccionesChG[nivel - 1] = valor
                            
                            if tipo == "ChB":
                                correccionesChB[nivel - 1] = valor

                        # Desestructuración de los arrays para asignarlos a las variables específicas
                        if tipo == "HN":
                            CorreccionHN1, CorreccionHN2, CorreccionHN3, CorreccionHN4, CorreccionHN5, CorreccionHN6, CorreccionHN7, CorreccionHN8, CorreccionHN9, CorreccionHN10, CorreccionHN11 = correccionesHN

                        if tipo == "Fallas":
                            CorreccionFallas1, CorreccionFallas2, CorreccionFallas3, CorreccionFallas4, CorreccionFallas5, CorreccionFallas6, CorreccionFallas7, CorreccionFallas8, CorreccionFallas9, CorreccionFallas10, CorreccionFallas11 = correccionesFallas

                        if tipo == "uHN":
                            CorreccionuHN1, CorreccionuHN2, CorreccionuHN3, CorreccionuHN4, CorreccionuHN5, CorreccionuHN6, CorreccionuHN7, CorreccionuHN8, CorreccionuHN9, CorreccionuHN10, CorreccionuHN11 = correccionesuHN

                        if tipo == "ChG":
                            CorreccionChG1, CorreccionChG2, CorreccionChG3, CorreccionChG4, CorreccionChG5, CorreccionChG6, CorreccionChG7, CorreccionChG8, CorreccionChG9, CorreccionChG10, CorreccionChG11 = correccionesChG

                        if tipo == "ChB":
                            CorreccionChB1, CorreccionChB2, CorreccionChB3, CorreccionChB4, CorreccionChB5, CorreccionChB6, CorreccionChB7, CorreccionChB8, CorreccionChB9, CorreccionChB10, CorreccionChB11 = correccionesChB

                    except Exception as e:
                        print(f"Se produjo un error al procesar las correcciones: {e}")
                        continue
                exitoso = all(await asyncio.gather(
                    self.escribirCorreccionesHN(correccionesHN, nivelesHN_node),
                    self.escribirCorreccionesuHN(correccionesuHN, nivelesuHN_node),
                    self.escribirCorreccionesChG(correccionesChG, nivelesChG_node),
                    self.escribirCorreccionesChB(correccionesChB, nivelesChB_node),
                    self.escribirCorreccionesFA(correccionesFallas, nivelesFA_node)
                ))

                if exitoso and exitosotorres:
                    self.confirmar_envio_correcciones(lista_datos_seleccionados.get("N_torre_proxima"), lista_datos_seleccionados.get("N_receta_proxima"), Comprobacion_datos_node)
                    print("Todas las correcciones se escribieron correctamente. Enviando confirmación.")
                else:
                    print("Error en alguna de las escrituras de correcciones. No se enviará confirmación.")
                    return {"mensaje": "Error en las correcciones."}
                
                return {"mensaje": "Proceso completado con éxito."}

            except Exception as e:
                logger.error(f"{e}")
                return {"mensaje": f"Error: {e}"}
        except Exception as e:
            logger.error(f"Sinconexion al servidor OPC UA-ORIGEN")
            await self.conexion_servidor.handle_reconnect()
            return {"mensaje": f"Error en la función leerDatosReceta: {e}"}

    async def escribirCorreccionesHN(self, correccionesHN, nivelesHN_node):
        global INDICE_OPC
        try:
            if not nivelesHN_node:
                logger.error("No se encontró el nodo 'DatosNivelesHN'.")
                return False

            for i, valor in enumerate(correccionesHN):
                if valor is not None:  # Solo escribir valores que no sean None
                    nodo_correccion = nivelesHN_node.get_child([f"{INDICE_OPC}:Correccion_hN{i+1}"])
                    if nodo_correccion:
                        data_value = ua.DataValue(ua.Variant(valor, ua.VariantType.Int16))
                        nodo_correccion.set_value(data_value)
                        print(f"Escrito Correccion_hN{i+1} con valor: {valor}")
                    else:
                        logger.error(f"No se encontró el nodo 'Correccion_hN{i+1}'.")

            return True

        except Exception as e:
            print(f"Error al escribir correcciones HN en OPC: {e}")
            return False

    async def escribirCorreccionesuHN(self, correccionesuHN, nivelesuHN_node):
        global INDICE_OPC
        try:
            if not nivelesuHN_node:
                logger.error("No se encontró el nodo 'DatosNivelesuHN'.")
                return False

            # Iterar sobre los valores de correccionesHN y escribir en los nodos OPC
            for i, valor in enumerate(correccionesuHN):
                if valor is not None:  # Solo escribir valores que no sean None
                    nodo_correccion = nivelesuHN_node.get_child([f"{INDICE_OPC}:ultimo_hNivel{i+1}"])
                    if nodo_correccion:
                        data_value = ua.DataValue(ua.Variant(valor, ua.VariantType.Int16))
                        nodo_correccion.set_value(data_value)
                        print(f"Escrito ultimo_hNivel{i+1} con valor: {valor}")
                    else:
                        logger.error(f"No se encontró el nodo 'ultimo_hNivel{i+1}'.")

            return True

        except Exception as e:
            print(f"Error al escribir correcciones uHN en OPC: {e}")
            return False

    async def escribirCorreccionesChG(self, correccionesChG, nivelesChG_node):
        global INDICE_OPC
        try:
            if not nivelesChG_node:
                logger.error("No se encontró el nodo 'DatosNivelesChG'.")
                return False

            for i, valor in enumerate(correccionesChG):
                if valor is not None:  # Solo escribir valores que no sean None
                    nodo_correccion = nivelesChG_node.get_child([f"{INDICE_OPC}:Correccion_hguardado_N{i+1}"])
                    if nodo_correccion:
                        data_value = ua.DataValue(ua.Variant(valor, ua.VariantType.Int16))
                        nodo_correccion.set_value(data_value)
                        print(f"Escrito Correccion_hguardado_N{i+1} con valor: {valor}")
                    else:
                        logger.error(f"No se encontró el nodo 'Correccion_hguardado_N{i+1}'.")

            return True

        except Exception as e:
            print(f"Error al escribir correcciones ChG en OPC: {e}")
            return False

    async def escribirCorreccionesChB(self, correccionesChB, nivelesChB_node):
        global INDICE_OPC
        try:
            if not nivelesChB_node:
                logger.error("No se encontró el nodo 'DatosNivelesChB'.")
                return False

            for i, valor in enumerate(correccionesChB):
                if valor is not None:  # Solo escribir valores que no sean None
                    nodo_correccion = nivelesChB_node.get_child([f"{INDICE_OPC}:Correccion_hbusqueda_N{i+1}"])
                    if nodo_correccion:
                        data_value = ua.DataValue(ua.Variant(valor, ua.VariantType.Int16))
                        nodo_correccion.set_value(data_value)
                        print(f"Escrito Correccion_hbusqueda_N{i+1} con valor: {valor}")
                    else:
                        logger.error(f"No se encontró el nodo 'Correccion_hbusqueda_N{i+1}'.")

            return True

        except Exception as e:
            print(f"Error al escribir correcciones ChB en OPC: {e}")
            return False

    async def escribirCorreccionesFA(self, correccionesFA, nivelesFA_node):
        global INDICE_OPC
        try:
            if not nivelesFA_node:
                logger.error("No se encontró el nodo 'DatosNivelesFA'.")
                return False

            for i, valor in enumerate(correccionesFA):
                if valor is not None:  # Solo escribir valores que no sean None
                    nodo_correccion = nivelesFA_node.get_child([f"{INDICE_OPC}:FallasN{i+1}"])
                    if nodo_correccion:
                        data_value = ua.DataValue(ua.Variant(valor, ua.VariantType.Int16))
                        nodo_correccion.set_value(data_value)
                        print(f"Escrito FallasN{i+1} con valor: {valor}")
                    else:
                        logger.error(f"No se encontró el nodo 'FallasN{i+1}'.")

            return True

        except Exception as e:
            print(f"Error al escribir correcciones FA en OPC: {e}")
            return False

    async def escribirDatosTorreOpc(self, datos_torre, e_datosTorre):
        global INDICE_OPC
        if not e_datosTorre:
            logger.error("No se encontró el nodo 'datosTorre'.")
            return False
        
        mapping = {
            "DisteNivel": "Correccion_DisteNivel",
            "hAjuste": "Correccion_hAjuste",
            "hAjusteN1": "Correccion_hAjusteN1",
            "hBastidor": "Correccion_hBastidor",
            "TAG": "TAG",
        }
        
        for db_field, opc_node in mapping.items():
            try:
                valor = datos_torre.get(db_field, None)
                if valor is not None:
                    nodo = e_datosTorre.get_child([f"{INDICE_OPC}:{opc_node}"])
                    if nodo is not None:
                        if isinstance(valor, str):
                            data_value = ua.DataValue(ua.Variant(valor, ua.VariantType.String))
                        else:
                            data_value = ua.DataValue(ua.Variant(valor, ua.VariantType.Int16))
                        
                        nodo.set_value(data_value)
                        logger.info(f"Escrito {db_field} -> {opc_node}: {valor}")
                    else:
                        logger.error(f"No se encontró el nodo OPC para {opc_node}.")
                        return False
                else:
                    logger.warning(f"El campo {db_field} no tiene valor para escribir.")
            except ua.UaError as e:
                logger.error(f"Error OPC UA escribiendo {opc_node}: {e}")
                return False
        
        return True
    
    async def confirmar_envio_correcciones(self, torre_proxima, receta_proxima, Comprobacion_datos_node):
        global INDICE_OPC
        try:
            if not Comprobacion_datos_node:
                logger.error("No se encontró el nodo 'Comprobacion_datos'.")
                return False

            confirmacion_envio = Comprobacion_datos_node.get_child([f"{INDICE_OPC}:confirmacion_envio"])
            torre_obtenido = Comprobacion_datos_node.get_child([f"{INDICE_OPC}:torre_obtenido"])
            receta_obtenido = Comprobacion_datos_node.get_child([f"{INDICE_OPC}:receta_obtenido"])

            confirmacion_envio.set_value(ua.DataValue(ua.Variant(1, ua.VariantType.Boolean)))
            torre_obtenido.set_value(ua.DataValue(ua.Variant(torre_proxima, ua.VariantType.Int16)))
            receta_obtenido.set_value(ua.DataValue(ua.Variant(receta_proxima, ua.VariantType.Int16)))

            print("Flanco activado en confirmacion_envio. Escribiendo valores de torre y receta...")

            def desactivar_flanco():
                time.sleep(3)
                confirmacion_envio.set_value(ua.DataValue(ua.Variant(0, ua.VariantType.Boolean)))
                print("Flanco desactivado en confirmacion_envio.")

            threading.Thread(target=desactivar_flanco, daemon=True).start()

            return True

        except Exception as e:
            print(f"Error en confirmar_envio_correcciones: {e}")
            return False
        
    async def gestorContraseñas(self):
        global estado_anterior_id_contra, INDICE_OPC
        try:
            root_node = await self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["2:ServerInterfaces"])


            server_interface_1 = server_interface_node.get_child([f"2:Server interface_1"])

            if not server_interface_1:
                logger.error("No se encontró 'Server interface_1'.")
                return False

            datos_opc_a_enviar = server_interface_1.get_child([f"{INDICE_OPC}:DATOS OPC A ENVIAR"])
            gestorContraseñas_node = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:Gestor_contraseña"])

            if not gestorContraseñas_node:
                print("No se encontró el nodo 'Gestor_contraseña'.")
                return False

            id_contra_node = gestorContraseñas_node.get_child([f"{INDICE_OPC}:id_contra"])
            if not id_contra_node:
                print("No se encontró el nodo 'id_contra'.")
                return False

            id_contra = id_contra_node.get_value()
            if not id_contra:
                print("El nodo 'id_contra' no tiene un valor válido.")
                return False

            fecha_inicio_node = gestorContraseñas_node.get_child([f"{INDICE_OPC}:fecha_inicio"])
            if not fecha_inicio_node:
                print("No se encontró el nodo 'fecha_inicio'.")
                return False

            valor_fecha_inicio = fecha_inicio_node.get_value()
            db: Session = next(get_db())

            try:
                contras_plc = db.query(ContrasPLC).filter(ContrasPLC.id == id_contra).first()
                fecha_actual = datetime.now()

                # Solo actualizar si id_contra cambia
                if estado_anterior_id_contra is None or estado_anterior_id_contra != id_contra:
                    estado_anterior_id_contra = id_contra  # Actualizar el estado anterior

                    if id_contra == 1:
                        fecha_bloqueo = fecha_actual + relativedelta(months=3)
                    else:
                        fecha_bloqueo = fecha_actual + timedelta(weeks=1)

                    if contras_plc:
                        contras_plc.fecha_inicio = fecha_actual
                        contras_plc.fecha_bloqueo = fecha_bloqueo
                        print(f"Fechas actualizadas para id_contra {id_contra}.")
                    else:
                        nueva_entrada = ContrasPLC(
                            id=id_contra,
                            fecha_inicio=fecha_actual,
                            fecha_bloqueo=fecha_bloqueo,
                            actualizar_id=0
                        )
                        db.add(nueva_entrada)
                        print(f"Fechas guardadas para nuevo id_contra {id_contra}.")

                    db.commit()

                if contras_plc and contras_plc.fecha_bloqueo == fecha_actual.date():
                    actualizar_id_node = gestorContraseñas_node.get_child([f"{INDICE_OPC}:actualizar_id"])
                    if not actualizar_id_node:
                        print("No se encontró el nodo 'actualizar_id'.")
                        return False

                    try:
                        data_value = ua.DataValue(ua.Variant(1, ua.VariantType.Boolean))
                        actualizar_id_node.set_value(data_value)
                        print(f"actualizar_id actualizado a True en OPC para id_contra {id_contra}.")
                    except ua.UaError as e:
                        print(f"Error OPC UA escribiendo 'actualizar_id': {e}")
                        return False

                if contras_plc:
                    contra_node = gestorContraseñas_node.get_child([f"{INDICE_OPC}:contra"])
                    if not contra_node:
                        print("No se encontró el nodo 'contra'.")
                        return False

                    try:
                        if isinstance(contras_plc.contra, str):
                            data_value = ua.DataValue(ua.Variant(contras_plc.contra, ua.VariantType.String))
                        else:
                            data_value = ua.DataValue(ua.Variant(contras_plc.contra, ua.VariantType.Int16))
                        contra_node.set_value(data_value)
                        print(f"Contraseña escrita en OPC para id_contra {id_contra}: {contras_plc.contra}")
                    except ua.UaError as e:
                        print(f"Error OPC UA escribiendo 'contra': {e}")
                        return False

                return True

            except Exception as e:
                db.rollback()
                print(f"Error al procesar los datos en la base de datos: {e}")
                return False

            finally:
                db.close()

        except Exception as e:
            print(f"Error en gestorContraseñas: {e}")
            return False

    def guardarRecetaEnBD(datosPLC):
        try:

            for index, (clave, datosReceta) in enumerate(datosPLC.items(), start=1):
                receta_id = index  # Matcheamos el índice + 1 con el ID

                if receta_id > 20:
                    print(f"Receta {receta_id} excede el límite de 20 y no será guardada.")
                    continue

                receta_existente = db_session.query(Recetario).filter(Recetario.id == receta_id).first()

                if receta_existente:
                    # Actualizamos los valores de la receta existente
                    receta_existente.altoMolde = datosReceta.get("ALTO DE MOLDE")
                    receta_existente.altoProducto = datosReceta.get("ALTO DE PRODUCTO")
                    receta_existente.ajusteAltura = datosReceta.get("ALTURA AJUSTE")
                    receta_existente.ajusteN1Altura = datosReceta.get("ALTURA AJUSTE N1")
                    receta_existente.bastidorAltura = datosReceta.get("ALTURA DE BASTIDOR")
                    receta_existente.n1Altura = datosReceta.get("ALTURA N1")
                    receta_existente.anchoProducto = datosReceta.get("ANCHO PRODUCTO")
                    receta_existente.cantidadNiveles = datosReceta.get("CANTIDAD NIVELES")
                    receta_existente.deltaNiveles = datosReceta.get("DELTA ENTRE NIVELES")
                    receta_existente.largoMolde = datosReceta.get("LARGO DE MOLDE")
                    receta_existente.largoProducto = datosReceta.get("LARGO DE PRODUCTO")
                    receta_existente.moldesNivel = datosReceta.get("MOLDES POR NIVEL")
                    receta_existente.codigoProducto = datosReceta.get("NOMBRE")
                    receta_existente.nroGripper = datosReceta.get("NUMERO DE GRIPPER")
                    receta_existente.pesoProducto = datosReceta.get("PESO DEL PRODUCTO")
                    receta_existente.tipoMolde = datosReceta.get("TIPO DE MOLDE")
                    receta_existente.productosMolde = datosReceta.get("PRODUCTOS POR MOLDE")
                    print(f"Receta {receta_id} actualizada correctamente.")
                else:
                    # Creamos una nueva receta si no existe
                    nueva_receta = Recetario(
                        id=receta_id,
                        altoMolde=datosReceta.get("ALTO DE MOLDE"),
                        altoProducto=datosReceta.get("ALTO DE PRODUCTO"),
                        ajusteAltura=datosReceta.get("ALTURA AJUSTE"),
                        ajusteN1Altura=datosReceta.get("ALTURA AJUSTE N1"),
                        bastidorAltura=datosReceta.get("ALTURA DE BASTIDOR"),
                        n1Altura=datosReceta.get("ALTURA N1"),
                        anchoProducto=datosReceta.get("ANCHO PRODUCTO"),
                        cantidadNiveles=datosReceta.get("CANTIDAD NIVELES"),
                        deltaNiveles=datosReceta.get("DELTA ENTRE NIVELES"),
                        largoMolde=datosReceta.get("LARGO DE MOLDE"),
                        largoProducto=datosReceta.get("LARGO DE PRODUCTO"),
                        moldesNivel=datosReceta.get("MOLDES POR NIVEL"),
                        codigoProducto=datosReceta.get("NOMBRE"),
                        nroGripper=datosReceta.get("NUMERO DE GRIPPER"),
                        pesoProducto=datosReceta.get("PESO DEL PRODUCTO"),
                        tipoMolde=datosReceta.get("TIPO DE MOLDE"),
                        productosMolde=datosReceta.get("PRODUCTOS POR MOLDE"),
                    )
                    db_session.add(nueva_receta)
                    print(f"Receta {receta_id} creada correctamente.")

            # Confirmamos todos los cambios realizados
            db_session.commit()

        except Exception as e:
            # Si hay un error, revertimos los cambios
            db_session.rollback()
            print(f"Error al guardar o actualizar las recetas en la base de datos: {e}")

        finally:
            # Cerramos la sesión de la base de datos
            db_session.close()
