from typing import Union
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import db
from config.opc import OPCUAClient
from config.ws import ws_manager

from models.receta import Recetas
from models.ciclo import Ciclo 
from models.etapa import Etapa
from models.torre import Torre
from models.recetaxciclo import RecetaXCiclo
from models.alarma import Alarma
from models.kuka import Kuka
from models.sdda import Sdda

from routers import usuariosRouter, pruebaTiempoRealHTTP, graficosHistorico, resumenProductividad
from service.datosTiempoReal import datosGenerale, resumenEtapaDesmoldeo, datosResumenCelda
from service.alarmasService import enviarDatosAlarmas, enviaListaLogsAlarmas

import socket
import asyncio
import logging

logger = logging.getLogger("uvicorn")
localIp = socket.gethostbyname(socket.gethostname())

URL = f"opc.tcp://{localIp}:4840"
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

async def central_opc_render():
    while True:
        try:
            logger.info("Leyendo valor del OPC centralmente...")
            data = {
                "desmoldeo": resumenEtapaDesmoldeo(opc_client),
                "general": datosGenerale(opc_client),
                "celda": datosResumenCelda(opc_client),
                "alarmas": enviarDatosAlarmas(opc_client),
                "alarmasLogs": enviaListaLogsAlarmas(),
            }
            logger.info(f"Datos leídos: {data}")
            await ws_manager.send_message("resumen-desmoldeo", data["desmoldeo"])
            await ws_manager.send_message("lista-tiempo-real", data["general"])
            await ws_manager.send_message("celda-completo", data["celda"]),
            await ws_manager.send_message("alarmas-datos", data["alarmas"]),
            await ws_manager.send_message("alarmas-logs", data["alarmasLogs"])

            await asyncio.sleep(10.0)  # Intervalo de lectura
        except Exception as e:
            logger.error(f"Error en el lector central del OPC: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        opc_client.connect()
        logger.info("Conectado al servidor OPC UA.")
        #await iniciar_evento()
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
app.include_router(pruebaTiempoRealHTTP.RouterLive)
app.include_router(graficosHistorico.RoutersGraficosH)
app.include_router(resumenProductividad.RouterProductividad)


@app.websocket("/ws/{id}")
async def resumen_desmoldeo(websocket: WebSocket, id: str):
    await websocket.accept()
    await ws_manager.connect(id, websocket)
    try:
        while True:
            # Esperar mensajes del cliente, si es necesario
            await websocket.receive_json()  # Aquí puedes hacer validaciones si es necesario
            data = resumenEtapaDesmoldeo(opc_client)  # Datos específicos para desmoldeo
            await ws_manager.send_message(id, data)
            await asyncio.sleep(0.300)
    except WebSocketDisconnect:
        await ws_manager.disconnect(id, websocket)

@app.get("/")
def read_root():
    return {"Hello": "World"}
