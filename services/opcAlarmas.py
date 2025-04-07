
from sqlalchemy.orm import Session
from config.db import get_db
from models.alarma import Alarma
from models.cicloDesmoldeo import CicloDesmoldeo
from models.alarmaHistorico import HistoricoAlarma
import logging
import re
import json
logger = logging.getLogger("uvicorn")

LISTA_COMPLETA_ALARMAS = {}


class OpcAlarmas:
    def __init__(self,conexion_servidor):
        self.conexion_servidor = conexion_servidor

    async def leerAlarmasRobot(self):
        global LISTA_COMPLETA_ALARMAS
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
            
            listaGeneralAlarmas = datos_opc_a_enviar.get_child(["4:Alarmas"])

            for child in listaGeneralAlarmas.get_children():
                
                tipo_alarma = {}
                for item in child.get_children():
                    print(f"LLEGUE AL PRIMER FOR ALARMAS")
                    browse_name = item.get_browse_name().Name
                    print(f"LLEGUE {browse_name}")
                    match = re.search(r"\[(\d+)\]", browse_name)

                    if not match:
                        logger.warning(f"No se encontró un índice entre corchetes en el nombre del nodo: '{browse_name}'")
                        continue  # Salta este nodo y sigue con el siguiente

                    indice = int(match.group(1))
                    valor = item.get_value()

                    if valor:
                        print("LLEGUEEEEEE!!!!!!!!!!!!")
                        try:
                            alarma_historico = HistoricoAlarma(
                                id_alarma = indice,
                                id_ciclo_desmoldado = self.get_ultimo_ciclo(db) or None, 
                                estadoAlarma=item.get_value()
                            )
                            db.add(alarma_historico)
                            logger.info(f"----------Se guardo con exito la alarma {item.get_browse_name().Name}")
                            db.commit()
                        except Exception as e:
                            logger.error(f"No se puedo guardar la alarma {item.get_browse_name().Name} {e}")

                    tipo_alarma[item.get_browse_name().Name] = item.get_value()
                LISTA_COMPLETA_ALARMAS[child.get_browse_name().Name] = tipo_alarma
            with open("alarmas.json", "w", encoding="utf-8") as archivo:
                json.dump(LISTA_COMPLETA_ALARMAS, archivo, indent=4, ensure_ascii=False)


            return "Se llego a crear el documentos de alarmas sin problemas"
        except Exception as e:
            logger.error(f"No se pudo leer los datos lista_alarmas {e}")

    def get_ultimo_ciclo(self, db):
            try:
                ultimo_ciclo = db.query(CicloDesmoldeo).order_by(CicloDesmoldeo.id.desc()).first()
                return ultimo_ciclo.id
            except Exception as e:
                logger.error(f"No hay datos en la BDD-CICLO")
            return None
        