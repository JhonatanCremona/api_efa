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

from datetime import datetime

import logging
import re
import threading
import time
import asyncio
import json

logger = logging.getLogger("uvicorn")
db_session = next(get_db())

estado_anterior_id_contra = None
LOGS_ALARMA_CICLO = []
ESTADO_CICLO_DESMOLDEO = None
TIEMPO_TRANSCURRIDO = 0
RECETA_ACTUAL = {}
LISTA_DATOS_CICLO = {}
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


ulEstado = None
tiempoCiclo = "00:00 mm:ss"
fechaInicioCIclo = 0

ultimo_estado = None 
ciclo_guardado = None
ULTIMO_NIVEL = None
PESO_ACTUAL_DESMOLDADO = None
PESO_TOTAL_CICLO = 0

error = "Error al obtener dato"
banda_desmolde = {
    1:"CINTA A",
    2:"CINTA B"
}
estado_maquina = {
    1: "CICLO INACTIVO",
    2: "CICLO ACTIVO",
    3: "CICLO PAUSADO"
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
    print(f"ULTIMO ESTADO CICLO TT: {ulEstado}")

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

class ObtenerNodosOpc:
    def __init__(self, conexion_servidor):
        self.conexion_servidor = conexion_servidor
    
    async def conexionOpcPLC(self):
        listaRespuesta = []

        global ESTADO_CICLO_DESMOLDEO, LISTA_DATOS_CICLO
        global LOGS_ALARMA_CICLO
        global TIEMPO_TRANSCURRIDO
        global RECETA_ACTUAL, lista_resumen_general, lista_sector_io
        global ultimo_estado, ciclo_guardado, ULTIMO_NIVEL, PESO_ACTUAL_DESMOLDADO

        try:
            
            root_node = await self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["3:ServerInterfaces"])

            server_interface_1 = server_interface_node.get_child(["4:Server interface_1"])
            if not server_interface_1:
                logger.error("No se encontró el nodo 'Server interface_1'.")
                return None

            datos_opc_a_enviar = server_interface_1.get_child(["4:DATOS OPC A ENVIAR"])
            
            estado_equipo = datos_opc_a_enviar.get_child([f"4:Estado_equipo"])
            e_sdda = datos_opc_a_enviar.get_child([f"4:datosSdda"])
            e_datosRobot = datos_opc_a_enviar.get_child([f"4:datosRobot"])
            e_datosGripper = datos_opc_a_enviar.get_child([f"4:datosGripper"])
            e_desmoldeo = datos_opc_a_enviar.get_child([f"4:desmoldeo"])
            e_datosSeleccionado = datos_opc_a_enviar.get_child([f"4:datosSeleccionados"])


            listaDatos = estado_equipo.get_children()
            for child in listaDatos:
                browse_name = child.get_browse_name().Name
                value = child.get_value()
                LISTA_DATOS_CICLO[browse_name] = value

                if browse_name == "Ciclo_iniciado":
                    ESTADO_CICLO_DESMOLDEO = value
                    if not value:
                        LOGS_ALARMA_CICLO.clear()

            print(f"ESTADO CICLO DES {ESTADO_CICLO_DESMOLDEO} - ULTIMO ESTADO: {ultimo_estado}")

            if ESTADO_CICLO_DESMOLDEO != ultimo_estado:
                if ESTADO_CICLO_DESMOLDEO == True:
                    
                    indiceRecetaActual = e_datosSeleccionado.get_child([f"4:N_receta_actual"]).get_value()
                    e_receta_actual = datos_opc_a_enviar.get_child([f"4:RECETARIO"]).get_child([f"4:[{indiceRecetaActual}]"])
                    childremRecetaA = e_receta_actual.get_children()
                    for child in childremRecetaA:
                        RECETA_ACTUAL[child.get_browse_name().Name] = child.get_value()
                    print(f"Receta Actual: {RECETA_ACTUAL.get("PESO DEL PRODUCTO")}")
                    
                    PESO_ACTUAL_DESMOLDADO = RECETA_ACTUAL.get("PESO DEL PRODUCTO", 0) * RECETA_ACTUAL.get("PRODUCTOS POR MOLDE", 0) * e_sdda.get_child([f"4:sdda_nivel_actual"]).get_value()
                    PESO_TOTAL_CICLO += PESO_ACTUAL_DESMOLDADO
                    ULTIMO_NIVEL = e_sdda.get_child([f"4:sdda_nivel_actual"]).get_value()

                    ciclo_desmoldeo = CicloDesmoldeo(
                            fecha_inicio= datetime.now(),
                            fecha_fin=None,
                            estadoMaquina= estado_maquina.get(estado_equipo.get_child([f"4:Estado_actual"]).get_value(), error),
                            bandaDesmolde= banda_desmolde.get(e_desmoldeo.get_child([f"4:desmoldeobanda"]).get_value(), error),
                            lote="001",
                            tiempoDesmolde=0.0,
                            pesoDesmoldado = 0,
                            id_etapa=1,
                            id_torre= 1 if e_datosSeleccionado.get_child([f"4:N_torre_actual"]).get_value() == 0 else e_datosSeleccionado.get_child([f"4:N_torre_actual"]).get_value()
                        )

                    lista_resumen_general["idRecetaActual"] = e_datosSeleccionado.get_child([f"N_receta_actual"]).get_value()
                    lista_resumen_general["idRecetaProxima"] = e_datosSeleccionado.get_child([f"N_receta_proxima"]).get_value()
                    lista_resumen_general["CodigoProducto"] = RECETA_ACTUAL.get("NOMBRE")
                    lista_resumen_general["TotalNiveles"] = RECETA_ACTUAL.get("CANTIDAD NIVELES")
                    lista_resumen_general["TipoMolde"] = tipo_molde.get(RECETA_ACTUAL.get("TIPO DE MOLDE"))
                    lista_resumen_general["estadoMaquina"] = estado_maquina.get(estado_equipo.get_child([f"4:Estado_actual"]).get_value(), error)
                    lista_resumen_general["desmoldeoBanda"] = banda_desmolde.get(e_desmoldeo.get_child([f"4:desmoldeobanda"]).get_value(), error)
                    lista_resumen_general["PesoProducto"] = PESO_ACTUAL_DESMOLDADO
                    lista_resumen_general["TiempoTranscurrido"] = TIEMPO_TRANSCURRIDO
                    lista_resumen_general["sdda_nivel_actual"] = ULTIMO_NIVEL
                    lista_resumen_general["NGripperActual"] = e_datosGripper.get_child([f"NGripperActual"]).get_value()
                    lista_resumen_general["PesoActualDesmoldado"] = PESO_TOTAL_CICLO
                    lista_resumen_general["TorreActual"] = e_datosSeleccionado.get_child([f"N_torre_actual"]).get_value()

                    try:
                        db_session.add(ciclo_desmoldeo)
                        db_session.commit()
                        logger.info(f"SE GUARDO EL CICLO - D: {ciclo_desmoldeo.id} ")
                        db_session.refresh(ciclo_desmoldeo)
                        ciclo_actual = ciclo_desmoldeo
                    except Exception as e:
                        db_session.rollback()
                        logger.error(f"ERRO AL GUARDAR CICLO-DESM EN BDD: {e}")


                    if ESTADO_CICLO_DESMOLDEO == False:
                        try:
                            ciclo_actualizar = db_session.query(CicloDesmoldeo).filter(CicloDesmoldeo.id == ciclo_actual.id).first()
                            db_recetaXCiclo = RecetarioXCiclo(
                                cantidadNivelesFinalizado = ULTIMO_NIVEL,
                                pesoPorNivel = PESO_ACTUAL_DESMOLDADO,
                                id_recetario = e_datosSeleccionado.get_child([f"4:N_receta_actual"]).get_value() if e_datosSeleccionado.get_child([f"4:N_receta_actual"]).get_value() <=5 else 2,
                                id_ciclo_desmoldeo = ciclo_actualizar.id,
                            )
                            db_session.add(db_recetaXCiclo)
                            db_session.commit()
                            print("------------------------------------------------")
                            logger.info("SE REGISTRO UN NUEVO CICLO EN LA RECETAXCICLO")

                            if ciclo_actualizar:
                                """
                                print(f"-----------DATO PESO ")
                                print(f"-DATO PESO{datosGenerales["PesoProducto"]} + {datosGenerales["sdda_nivel_actual"]} :  {datosGenerales["PesoProducto"] * datosGenerales["sdda_nivel_actual"]}-")
                                """
                                ciclo_actualizar.fecha_fin = datetime.now()
                                ciclo_actualizar.pesoDesmoldado = PESO_ACTUAL_DESMOLDADO
                                ciclo_actualizar.tiempoDesmolde = int((datetime.now() - ciclo_actualizar.fecha_inicio).total_seconds() // 60)
                                db_session.commit()
                                db_session.refresh(ciclo_actualizar)
                                logger.info(f"Ciclo actualizado con ID: {ciclo_actualizar.id}")
                                PESO_ACTUAL_DESMOLDADO = 0;
                                PESO_TOTAL_CICLO = 0
                                ULTIMO_NIVEL= 0;

                        except Exception as e:
                            logger.error(f"SURGIO UN ERROR AL GUARDAR UN REGISTRO CICLOXRECETA {e}")
                
            ultimo_estado = ESTADO_CICLO_DESMOLDEO
            TIEMPO_TRANSCURRIDO = obtenerTiempo(ESTADO_CICLO_DESMOLDEO)
            listaRespuesta.append(lista_resumen_general)

            lista_sector_io["banda_desmoldeo"] = banda_desmolde.get(e_desmoldeo.get_child([f"4:desmoldeobanda"]).get_value(), error)
            lista_sector_io["estado_ciclo"] = ESTADO_CICLO_DESMOLDEO

            listaCelda, listaDatosGeneral = await asyncio.gather(
                self.obtenerDatosCelda(
                    estado_equipo.get_child(f"4:Estado_actual").get_value(), 
                    e_sdda.get_child(f"4:sdda_nivel_actual").get_value()
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

            return listaRespuesta
        
        except Exception as e:
            logger.exception("Error al obtener la conexión OPC del PLC:")
            await self.conexion_servidor.handle_reconnect()
            return None
        

    async def actualizarRecetas(self):
        global PANTALLA_ENCENDIDA, ULTIMO_ESTADO_PANTALLA
        lista_recetas = {}
        
        try:
            root_node = await self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["3:ServerInterfaces"])

            server_interface_1 = server_interface_node.get_child(["4:Server interface_1"])
            if not server_interface_1:
                logger.error("No se encontró el nodo 'Server interface_1'.")
                return None

            datos_opc_a_enviar = server_interface_1.get_child(["4:DATOS OPC A ENVIAR"])
            e_datosSeleccionado = datos_opc_a_enviar.get_child([f"4:datosSeleccionados"])
            e_listaRecetario = datos_opc_a_enviar.get_child([f"4:RECETARIO"])

            logger.info("LEEEEEEEEE")

            pantalla_receta = e_datosSeleccionado.get_child([f"4:pantalla_receta"])
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
        global RECETA_ACTUAL
        try:

            resultado["Nombre actual"] = RECETA_ACTUAL.get("NOMBRE")
            resultado["PesoProducto"] = RECETA_ACTUAL.get("PESO DEL PRODUCTO")
            resultado["TotalNiveles"] = RECETA_ACTUAL.get("CANTIDAD NIVELES")

            resultado["sdda_nivel_actual"] = sddaNivelActual
            resultado["estadoMaquina"] = estado_maquina.get(estadoActual)
            resultado["iniciado"] = ESTADO_CICLO_DESMOLDEO

            # Evitar TypeError en caso de valores None
            peso_producto = resultado.get("PesoProducto", 0)
            nivel_actual = resultado.get("sdda_nivel_actual", 0)

            print(f"VALOR DE PESO PRODUCTO: {resultado.get("PesoProducto")}")

            resultado["PesoActualDesmoldado"] = (peso_producto or 0) * nivel_actual
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
        global RECETA_ACTUAL
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
        lista_datos_seleccionados = {}
        try:
            db: Session = next(get_db())
            root_node = await self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["3:ServerInterfaces"])

            server_interface_1 = server_interface_node.get_child(["4:Server interface_1"])
            if not server_interface_1:
                logger.error("No se encontró el nodo 'Server interface_1'.")
                return None

            datos_opc_a_enviar = server_interface_1.get_child(["4:DATOS OPC A ENVIAR"])
            e_datosSeleccionado = datos_opc_a_enviar.get_child([f"4:datosSeleccionados"])

            e_datosTorre = datos_opc_a_enviar.get_child(["4:datosTorre"])
            nivelesHN_node = datos_opc_a_enviar.get_child(["4:DatosNivelesHN"])
            nivelesuHN_node = datos_opc_a_enviar.get_child(["4:DatosNivelesuHN"])
            nivelesChG_node = datos_opc_a_enviar.get_child(["4:DatosNivelesChG"])
            nivelesChB_node = datos_opc_a_enviar.get_child(["4:DatosNivelesChB"])
            nivelesFA_node = datos_opc_a_enviar.get_child(["4:DatosNivelesFA"])

            Comprobacion_datos_node = datos_opc_a_enviar.get_child(["4:Comprobacion_datos"])

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
        try:
            if not nivelesHN_node:
                logger.error("No se encontró el nodo 'DatosNivelesHN'.")
                return False

            for i, valor in enumerate(correccionesHN):
                if valor is not None:  # Solo escribir valores que no sean None
                    nodo_correccion = nivelesHN_node.get_child([f"4:Correccion_hN{i+1}"])
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
        try:
            if not nivelesuHN_node:
                logger.error("No se encontró el nodo 'DatosNivelesuHN'.")
                return False

            # Iterar sobre los valores de correccionesHN y escribir en los nodos OPC
            for i, valor in enumerate(correccionesuHN):
                if valor is not None:  # Solo escribir valores que no sean None
                    nodo_correccion = nivelesuHN_node.get_child([f"4:ultimo_hNivel{i+1}"])
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
        try:
            if not nivelesChG_node:
                logger.error("No se encontró el nodo 'DatosNivelesChG'.")
                return False

            for i, valor in enumerate(correccionesChG):
                if valor is not None:  # Solo escribir valores que no sean None
                    nodo_correccion = nivelesChG_node.get_child([f"4:Correccion_hguardado_N{i+1}"])
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
        try:
            if not nivelesChB_node:
                logger.error("No se encontró el nodo 'DatosNivelesChB'.")
                return False

            for i, valor in enumerate(correccionesChB):
                if valor is not None:  # Solo escribir valores que no sean None
                    nodo_correccion = nivelesChB_node.get_child([f"4:Correccion_hbusqueda_N{i+1}"])
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
        try:
            if not nivelesFA_node:
                logger.error("No se encontró el nodo 'DatosNivelesFA'.")
                return False

            for i, valor in enumerate(correccionesFA):
                if valor is not None:  # Solo escribir valores que no sean None
                    nodo_correccion = nivelesFA_node.get_child([f"4:FallasN{i+1}"])
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
                    nodo = e_datosTorre.get_child([f"4:{opc_node}"])
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

        try:
            if not Comprobacion_datos_node:
                logger.error("No se encontró el nodo 'Comprobacion_datos'.")
                return False

            confirmacion_envio = Comprobacion_datos_node.get_child(["4:confirmacion_envio"])
            torre_obtenido = Comprobacion_datos_node.get_child(["4:torre_obtenido"])
            receta_obtenido = Comprobacion_datos_node.get_child(["4:receta_obtenido"])

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
        global estado_anterior_id_contra
        try:
            root_node = await self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["3:ServerInterfaces"])

            server_interface_1 = server_interface_node.get_child(["4:Server interface_1"])
            if not server_interface_1:
                logger.error("No se encontró 'Server interface_1'.")
                return False

            datos_opc_a_enviar = server_interface_1.get_child(["4:DATOS OPC A ENVIAR"])
            gestorContraseñas_node = datos_opc_a_enviar.get_child(["4:Gestor_contraseña"])

            if not gestorContraseñas_node:
                print("No se encontró el nodo 'Gestor_contraseña'.")
                return False

            id_contra_node = gestorContraseñas_node.get_child(["4:id_contra"])
            if not id_contra_node:
                print("No se encontró el nodo 'id_contra'.")
                return False

            id_contra = id_contra_node.get_value()
            if not id_contra:
                print("El nodo 'id_contra' no tiene un valor válido.")
                return False

            fecha_inicio_node = gestorContraseñas_node.get_child(["4:fecha_inicio"])
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
                    actualizar_id_node = gestorContraseñas_node.get_child(["4:actualizar_id"])
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
                    contra_node = gestorContraseñas_node.get_child(["4:contra"])
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