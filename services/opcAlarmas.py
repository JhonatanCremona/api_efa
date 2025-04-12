
from sqlalchemy.orm import Session
from datetime import datetime

from config.db import get_db

from models.alarma import Alarma
from models.cicloDesmoldeo import CicloDesmoldeo
from models.alarmaHistorico import HistoricoAlarma
import logging
import re
import json
logger = logging.getLogger("uvicorn")

LISTA_COMPLETA_ALARMAS = {}
LISTA_FRONT_ALARMAS = []

class OpcAlarmas:
    def __init__(self,conexion_servidor):
        self.conexion_servidor = conexion_servidor

    async def leerAlarmasRobot(self):
        global LISTA_COMPLETA_ALARMAS, LISTA_FRONT_ALARMAS
        dict_unico_alarmas = {}
        grupo_nombre = None
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
                logger.debug(f"[FOR-ALARMAS] Evaluando item en grupo '{grupo_nombre}'")
                grupo_nombre = child.get_browse_name().Name
                logger.info(f"[INICIO] Grupo de alarma detectado: '{grupo_nombre}'")
                
                tipo_alarma = {}
                item_alarma = {}

                for item in child.get_children():
                    
                    logger.debug(f"[FOR-ALARMAS] Evaluando item en grupo '{grupo_nombre}'")

                    browse_name = item.get_browse_name().Name
                    match = re.search(r"\[(\d+)\]", browse_name)

                    if not match:
                        logger.warning(f"[SKIP] Nodo sin índice en nombre: '{browse_name}'")
                        continue

                    indice = int(match.group(1))
                    valor = item.get_value()

                    if grupo_nombre == "SDDA":
                        indice+= 100
                    if grupo_nombre == "FALLAS CILINDROS":
                        indice+=200
                    if grupo_nombre == "POSICIONADOR":
                        indice+=300
                    if grupo_nombre == "GENERALES":
                        indice+=400
                    if grupo_nombre == "SERVOS":
                        indice+=500
                    if grupo_nombre == "INICIO DE CICLO":
                        indice+=600
                    if grupo_nombre == "CANCELACION":
                        indice+=700
                    if grupo_nombre == "PULSADORES":
                        indice+=800
                    logger.info(f"[VALOR] Alarma '{browse_name}' (ID: {indice}) - Valor leído: {valor}")
                    alarma_existente = db.query(Alarma).filter_by(id=indice).first()

                    if valor == True:
                        try:
                            if not alarma_existente:
                                nueva_alarma = Alarma(
                                    id=indice,
                                    tipoAlarma=grupo_nombre,
                                    descripcion=""
                                )
                                db.add(nueva_alarma)
                                db.commit()
                                logger.info(f"[CREADO] Se agregó la alarma faltante con ID {indice} y tipo '{grupo_nombre}'")

                            alarma_historico = HistoricoAlarma(
                                id_alarma=indice,
                                id_ciclo_desmoldeo = self.get_ultimo_ciclo(db),
                                estadoAlarma = valor
                            )
                            db.add(alarma_historico)
                            db.commit()
                            logger.info(f"[GUARDADO] Se registró la alarma '{browse_name}' con ID {indice} y estado '{valor}'")
                        except Exception as e:
                            db.rollback()
                            logger.error(f"[ERROR-DB] Fallo al guardar alarma '{browse_name}' (ID: {indice}) - Error: {e}")
                            
                    if alarma_existente:
                        item_alarma = {
                            "id_alarma": alarma_existente.id,
                            "estadoAlarma": valor,
                            "tipoAlarma": alarma_existente.tipoAlarma,
                            "descripcion": alarma_existente.descripcion,
                            "fechaRegistro": datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                        }
                        dict_unico_alarmas[alarma_existente.id] = item_alarma
                        

                    tipo_alarma[item.get_browse_name().Name] = item.get_value()
                LISTA_COMPLETA_ALARMAS[child.get_browse_name().Name] = tipo_alarma
            
            with open("alarmas.json", "w", encoding="utf-8") as archivo:
                json.dump(dict_unico_alarmas, archivo, indent=4, ensure_ascii=False)
            return "Se llego a crear el documentos de alarmas sin problemas"
        
        except Exception as e:
            logger.error(f"No se pudo leer los datos lista_alarmas {e}")

    def get_ultimo_ciclo(self, db):
            try:
                ultimo_ciclo = db.query(CicloDesmoldeo).order_by(CicloDesmoldeo.id.desc()).first()
                if not ultimo_ciclo:
                    logger.error(f"No existen datos en la tabla Ciclo")
                    return None
                return ultimo_ciclo.id
            except Exception as e:
                logger.error(f"No hay datos en la BDD-CICLO")
        