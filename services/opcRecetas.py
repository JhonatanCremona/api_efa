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

import logging
import os

PANTALLA_ENCENDIDA = False
ULTIMO_ESTADO_PANTALLA = None

logger = logging.getLogger("uvicorn")
INDICE_OPC = os.getenv("INDICE_OPC_UA")
db_session = next(get_db())
class OpcRecetas:
    def __init__(self, conexion_servidor):
        self.conexion_servidor = conexion_servidor

    async def actualizarRecetas(self):
        global PANTALLA_ENCENDIDA, ULTIMO_ESTADO_PANTALLA, INDICE_OPC
        lista_recetas = {}
        
        try:
            root_node = await self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["3:ServerInterfaces"])

            server_interface_1 = server_interface_node.get_child([f"{INDICE_OPC}:Server interface_1"])
            if not server_interface_1:
                logger.error("No se encontró el nodo 'Server interface_1'.")
                return None

            datos_opc_a_enviar = server_interface_1.get_child([f"{INDICE_OPC}:DATOS OPC A ENVIAR"])
            e_datosSeleccionado = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:datosSeleccionados"])
            e_listaRecetario = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:RECETARIO"])

            pantalla_receta = e_datosSeleccionado.get_child([f"{INDICE_OPC}:pantalla_receta"])
            PANTALLA_ENCENDIDA = pantalla_receta.get_value()
            logger.info(f"PANTALLA OPC: {PANTALLA_ENCENDIDA}")
            

            if PANTALLA_ENCENDIDA != ULTIMO_ESTADO_PANTALLA :
                if PANTALLA_ENCENDIDA == True:
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
            logger.error(f"Error al intertar ACTUALIZAR RECETAS, problema de conexion {e}") 
            await self.conexion_servidor.handle_reconnect()

    def guardarRecetaEnBD(self, datosPLC):
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