from typing import Union
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime

from config import db
from config.opc import OPCUAClient
from config.ws import ws_manager

from models.ciclo import Ciclo 
from models.etapa import Etapa
from models.torre import Torre
from models.recetaxciclo import RecetaXCiclo
from models.alarma import Alarma
from models.kuka import Kuka
from models.sdda import Sdda

from routers import usuariosRouter, graficosHistorico, resumenProductividad
from service.datosTiempoReal import datosGenerale, resumenEtapaDesmoldeo, datosResumenCelda
from service.alarmasService import enviarDatosAlarmas, enviaListaLogsAlarmas

import socket
import asyncio
import logging
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger("uvicorn")
localIp = socket.gethostbyname(socket.gethostname())

opc_ip = os.getenv("OPC_SERVER_IP")
opc_port = os.getenv("OPC_SERVER_PORT")

URL = f"opc.tcp://{opc_ip}:{opc_port}"
opc_client = OPCUAClient(URL)

#db.Base.metadata.drop_all(bind=db.engine)
db.Base.metadata.create_all(bind=db.engine)

"""
async def iniciar_evento():
    logger.info("Entré al método iniciar_evento")
    
    async def leer_opc_y_enviar():
        while True:
            try:
                logger.info("Leyendo valor del OPC...")
                data = resumenEtapaDesmoldeo(opc_client)
                await ws_manager.send_message("123", {"value": data})
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.error(f"Error al leer o enviar el valor: {e}")
    
    logger.info("Creando tarea para leer OPC y enviar mensajes.")
    asyncio.create_task(leer_opc_y_enviar())
"""

ultimo_estado = None 
ciclo_guardado = None
pesoActual = 0
async def central_opc_render():
    global ultimo_estado, ciclo_guardado, pesoActual
    while True:
        try:    
            
            #logger.info("Leyendo valor del OPC centralmente...")
            data = {
                "desmoldeo": resumenEtapaDesmoldeo(opc_client),
                "general": datosGenerale(opc_client),
                "celda": datosResumenCelda(opc_client),
                "alarmas": enviarDatosAlarmas(opc_client),
                "alarmasLogs": enviaListaLogsAlarmas(),
            }
            await ws_manager.send_message("resumen-desmoldeo", data["desmoldeo"])
            await ws_manager.send_message("lista-tiempo-real", data["general"])
            await ws_manager.send_message("celda-completo", data["celda"]),
            await ws_manager.send_message("alarmas-datos", data["alarmas"]),
            await ws_manager.send_message("alarmas-logs", data["alarmasLogs"])
            await ws_manager.send_message("lista-datos-ws", data)
            
            datosGenerales = data["desmoldeo"] 
            estado_actual = datosGenerales["iniciado"] 
            print("--------------------------------")
            logger.info(f"ESTADO ACTUAL {estado_actual} - ULTIMO ESTADO: {ultimo_estado}")
            if estado_actual != ultimo_estado:
                logger.info(f"ESTADO DEL CICLO {ultimo_estado}")
                pesoActual = datosGenerales["PesoActualDesmoldado"]
                if estado_actual == True:
                    logger.info("LLEGUE AL IF GUARDA DATOS")
                    pesoActual = datosGenerales["PesoActualDesmoldado"] if datosGenerales["PesoActualDesmoldado"] > 0 else pesoActual;
                    db_ciclo = Ciclo(
                        fecha_inicio= datetime.now(),
                        fecha_fin=None,
                        estadoMaquina=datosGenerales["estadoMaquina"],
                        bandaDesmolde=datosGenerales["desmoldeobanda"], 
                        lote="001",
                        tiempoDesmolde=0.0,
                        pesoDesmoldado = 0,
                        id_etapa=1,
                        id_torre= 1 if datosGenerales["torreActual"] == 0 else datosGenerales["torreActual"],
                    )
                    
                    db_session: Session = db.get_db().__next__()
                    logger.info("ME CONECTE A LOS LOS DATOS A LA BASE")
                    try:
                        db_session.add(db_ciclo)
                        db_session.commit()
                        logger.info("GUARDE DATOS EN LA BSSSS")
                        logger.info(f"Ciclo creado con ID: {db_ciclo.id}")
                        db_session.refresh(db_ciclo) 
                        ciclo_guardado = db_ciclo 
                    except Exception as e:
                        db_session.rollback()
                        logger.error(f"Error al guardar el ciclo: {e}")
                    finally:
                        db_session.close()
                elif estado_actual == False:
                    print("------------------------------------------------")
                    logger.info("PUEDO ACTUALIZAAAAR EL DATO")
                    try:
                        db_session: Session = db.get_db().__next__()
                        logger.info("ME CONECTE A LA BASE PARA ACTUALIZAR")
                        ciclo_actual = db_session.query(Ciclo).filter(Ciclo.id == ciclo_guardado.id).first()
                        db_recetaXCiclo = RecetaXCiclo(
                            cantidadNivelesFinalizado = datosGenerales["sdda_nivel_actual"], 
                            pesoPorNivel = datosGenerales["PesoProducto"],
                            id_recetario = datosGenerales["idRecetaActual"] if datosGenerales["idRecetaActual"]<=5 else 2,
                            id_ciclo = ciclo_actual.id,
                        )
                        db_session.add(db_recetaXCiclo)
                        db_session.commit()

                        if ciclo_actual:
                            print(f"-----------DATO PESO {datosGenerales["PesoActualDesmoldado"]}")
                            print(f"-DATO PESO{datosGenerales["PesoProducto"]} + {datosGenerales["sdda_nivel_actual"]} :  {datosGenerales["PesoProducto"] * datosGenerales["sdda_nivel_actual"]}-")
                            ciclo_actual.fecha_fin = datetime.now()
                            ciclo_actual.pesoDesmoldado = pesoActual * 10
                            ciclo_actual.tiempoDesmolde = datosGenerales["cicloTiempoTotal"]
                            db_session.commit()
                            db_session.refresh(ciclo_actual)
                            logger.info(f"Ciclo actualizado con ID: {ciclo_actual.id}")
                            pesoActual = 0;
                    except Exception as e:
                        db_session.rollback()
                        logger.error(f"Error al actualizar el ciclo: {e}")

            ultimo_estado = estado_actual
            
            await asyncio.sleep(0.5) 
        except Exception as e:
            db.rollback()
            logger.error(f"Error en el lector central del OPC: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        opc_client.connect()
        logger.info("Conectado al servidor OPC UA.")
        asyncio.create_task(central_opc_render())
        yield
    finally:
        opc_client.disconnect()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas las solicitudes de cualquier dominio
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los headers
)

app.include_router(usuariosRouter.RouterUsers)
#app.include_router(pruebaTiempoRealHTTP.RouterLive)
app.include_router(graficosHistorico.RoutersGraficosH)
app.include_router(resumenProductividad.RouterProductividad)


@app.websocket("/ws/{id}")
async def resumen_desmoldeo(websocket: WebSocket, id: str):
    await websocket.accept()
    await ws_manager.connect(id, websocket)
    try:
        while True:
            await websocket.receive_json()  # Aquí puedes hacer validaciones si es necesario
            data = resumenEtapaDesmoldeo(opc_client)  #SE PUEDE ELIMINAR ?
            await ws_manager.send_message(id, data)
            await asyncio.sleep(0.10)
    except WebSocketDisconnect:
        await ws_manager.disconnect(id, websocket)

@app.get("/")
def read_root():
        value = opc_client.read_node(f"ns=4;i=22")
        return {"nodo id": 2, "value": value}
