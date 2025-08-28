from sqlalchemy.orm import Session
from datetime import datetime
from threading import Lock
from config.db import get_db

from models.alarma import Alarma
from models.cicloDesmoldeo import CicloDesmoldeo
from models.alarmaHistorico import HistoricoAlarma

import re
import json
import os
import logging
import threading
import time

logger = logging.getLogger(__name__)
logger = logging.getLogger("uvicorn")

LISTA_COMPLETA_ALARMAS = {}
LISTA_FRONT_ALARMAS = []
INDICE_OPC = os.getenv("INDICE_OPC_UA")

class OpcAlarmas:
    def __init__(self,conexion_servidor):
        self.conexion_servidor = conexion_servidor
        self.alarmas_activas = {}   # id_alarma -> datetime de inicio
        self.alarmas_lock = Lock() 

    async def leerAlarmasCeldaDesmoldeo(self):
        global INDICE_OPC
        dict_unico_alarmas = {}
        lock_dict = Lock()
        try:
            #root_node = asyncio.run(self.conexion_servidor.get_objects_nodos())  # Llamada fuera del hilo async
            root_node = await self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["2:ServerInterfaces"])
            server_interface_1 = server_interface_node.get_child([f"2:Server interface_1"])
            datos_opc_a_enviar = server_interface_1.get_child([f"{INDICE_OPC}:DATOS OPC A ENVIAR"])
            listaGeneralAlarmas = datos_opc_a_enviar.get_child([f"{INDICE_OPC}:Alarmas"])
            
            tipos_alarmas = [
                "SDDA", "FALLAS CILINDROS", "POSICIONADOR", "GENERALES",
                "SERVOS", "INICIO DE CICLO", "CANCELACION", "PULSADORES","ROBOT"
            ]

            hilos = []

            for tipo in tipos_alarmas:
                t = threading.Thread(
                    #name=f"Hilo-{tipo}",
                    target=self.medicion_con_tiempo,
                    args=(tipo, listaGeneralAlarmas, dict_unico_alarmas, lock_dict)
                )
                hilos.append(t)
                t.start()

            for t in hilos:
                t.join()

            print(f"Total de ALARMAS RECOPILADOS: {len(dict_unico_alarmas)}")

            with open("alarmas.json", "w", encoding="utf-8") as archivo:
                json.dump(dict_unico_alarmas, archivo, indent=4, ensure_ascii=False)

            return "Se creó el documento de alarmas correctamente"

        except Exception as e:
            logger.error(f"Error al leer las alarmas: {e}")
            await self.conexion_servidor.handle_reconnect()

    def medicion_con_tiempo(self, tipo, listaGeneralAlarmas, dict_unico_alarmas, lock_dict):
        inicio = time.perf_counter()
        try:
            self.obtenerDatosTipoAlrma(tipo, listaGeneralAlarmas, dict_unico_alarmas, lock_dict)
        finally:
            fin = time.perf_counter()
            duracion = fin - inicio
            print(f"[TIEMPO] Hilo '{tipo}' ejecutado en {duracion:.4f} segundos")

    def get_ultimo_ciclo(self, db):
            try:
                ultimo_ciclo = db.query(CicloDesmoldeo).order_by(CicloDesmoldeo.id.desc()).first()
                if not ultimo_ciclo:
                    logger.error(f"No existen datos en la tabla Ciclo")
                    return None
                return ultimo_ciclo.id
            except Exception as e:
                logger.error(f"No hay datos en la BDD-CICLO")

    def obtener_offset(self, tipo):
        offsets = {
            "SDDA": 100,
            "FALLAS CILINDROS": 200,
            "POSICIONADOR": 300,
            "GENERALES": 400,
            "SERVOS": 500,
            "INICIO DE CICLO": 600,
            "CANCELACION": 700,
            "PULSADORES": 800,
            "ROBOT": 0
        }
        return offsets.get(tipo, 0)

    def obtenerDatosTipoAlrma(self, nodo_opc, tipo_alarma, dict_unico_alarmas, lock_dict):
        global INDICE_OPC
        db: Session = next(get_db())
        logger.info(f"Se esta ejecutando el sistema de: {nodo_opc}")
        ahora = datetime.now()

        try:
            alarma = tipo_alarma.get_child([f"{INDICE_OPC}:{nodo_opc}"])
            children = alarma.get_children()
            
            # Leer todos los valores en una sola llamada
            try:
                valores = self.conexion_servidor.read_multiple_values(children)
            except AttributeError:
                # fallback seguro (uno a uno) por si el cliente no soporta lectura bulk
                valores = [child.get_value() for child in children]


            for item, valor in zip(children, valores):
                browse_name = item.get_browse_name().Name
                match = re.search(r"\[(\d+)\]", browse_name)
                if not match:
                    logger.info(f"[SKIP] Nodo sin índice en nombre: '{browse_name}'")
                    continue

                indice = int(match.group(1))
                offset = self.obtener_offset(nodo_opc)
                indice += offset

                alarma_existente = db.query(Alarma).filter_by(id=indice).first()
                if valor is True:
                    if indice not in self.alarmas_activas:
                        if not alarma_existente:
                            try:
                                nueva_alarma = Alarma(
                                    id=indice,
                                    tipoAlarma=nodo_opc,
                                    descripcion=""
                                )
                                db.add(nueva_alarma)
                                db.commit()
                                logger.info(f"[CREADO] Se agregó la alarma faltante con ID {indice} y tipo '{nodo_opc}'")
                            except Exception as e:
                                db.rollback()
                                print(f"ERROR- AL GUARDAR DATO DE ALARMA NUEVA: {e}")
                        # NUEVA ALARMA - Iniciar seguimiento
                        self.alarmas_activas[indice] = ahora
                        # Guardar inicio en base de datos
                        try:
                            alarma_historico = HistoricoAlarma(
                                id_alarma=indice,
                                id_ciclo_desmoldeo=self.get_ultimo_ciclo(db),
                                estadoAlarma=True,
                                tiempo_inicio=ahora
                            )
                            db.add(alarma_historico)
                            db.commit()
                        except Exception as e:
                            db.rollback()
                            print(f"ERROR - AL GUARDAR ALARMA EN BDD {e}")
                elif valor is False and indice in self.alarmas_activas:
                    inicio = self.alarmas_activas.pop(indice)
                    duracion_minutos = (ahora - inicio).total_seconds() / 60
                    # Guardar cierre en base de datos (como nuevo registro o actualización del anterior)
                    try:
                        alarma_historico = HistoricoAlarma(
                            id_alarma=indice,
                            id_ciclo_desmoldeo=self.get_ultimo_ciclo(db),
                            estadoAlarma=False,
                            tiempo_inicio=inicio,
                            tiempo_fin=ahora,
                            duracion_minutos=duracion_minutos
                        )
                        db.add(alarma_historico)
                        db.commit()
                    except Exception as e:
                        db.rollback()
                        print(f"ERROR- AL GUARDAR ALARMA EN LA TABLA HISTORICO: {e}")

                if alarma_existente:
                    item_alarma = {
                        "id_alarma": alarma_existente.id,
                        "estadoAlarma": valor,
                        "tipoAlarma": alarma_existente.tipoAlarma,
                        "descripcion": alarma_existente.descripcion,
                        "fechaRegistro": datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                    }
                    with lock_dict:
                        print(f"TOTAL DE ALARMAS RECOPILADAS HILO[{nodo_opc}]: {len(dict_unico_alarmas)}")
                        dict_unico_alarmas[alarma_existente.id] = item_alarma

        except Exception as e:
            print(f"[ERROR THREAD ALARMA] Nodo: {nodo_opc} - {e}")
        finally:
            db.close()
