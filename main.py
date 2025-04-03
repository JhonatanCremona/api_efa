from typing import Union
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import text

from config.opc import OPCUAClient
from config import db
from config.ws import ws_manager
from services.opcService import ObtenerNodosOpc

from models.recetario import Recetario
from models.alarma import Alarma
from models.alarmaHistorico import HistoricoAlarma
from models.cicloDesmoldeo import CicloDesmoldeo
from models.recetarioXCiclo import RecetarioXCiclo
from models.robot import Robot
from models.sdda import Sdda
from models.torre import Torre
from models.torreconfiguraciones import TorreConfiguraciones
from models.usuario import Usuario 
from models.etapa import Etapa
from services.desp import bcrypt_context
from routers import usuarios, graficosHistorico, productividad

import logging
import asyncio
import socket

from dotenv import load_dotenv
import os

ruta_principal = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger("uvicorn")

opc_ip = os.getenv("OPC_SERVER_IP")
opc_port = os.getenv("OPC_SERVER_PORT")

ruta_sql_alarmas = os.path.join(ruta_principal, 'query', 'insert_alarmas.sql')
ruta_sql_etapas = os.path.join(ruta_principal, 'query', 'insert_etapas.sql')
ruta_sql_recetario = os.path.join(ruta_principal, 'query', 'insert_recetario.sql')
ruta_sql_torre = os.path.join(ruta_principal,'query', 'insert_torre.sql')


URL = f"opc.tcp://{opc_ip}:{opc_port}"
opc_client = OPCUAClient(URL)

db.Base.metadata.drop_all(bind=db.engine)
db.Base.metadata.create_all(bind=db.engine)

listaDatosOpc = ObtenerNodosOpc(opc_client)
listaRecetario = ObtenerNodosOpc(opc_client)

def cargar_archivo_sql(file_path: str):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding="utf-8") as file:
                sql_cript_alarma = file.read()
            
            with db.engine.connect() as conn:
                conn.execute(text(sql_cript_alarma))  
                conn.commit()
                logger.info(f"Archivo SQL ejecutado correctamente desde {file_path}")
        else:
            logger.error(f"El archivo {file_path} no existe.")
    except Exception as e:
        logger.error(f"Error al cargar el archivo SQL: {e}")

async def central_opc_render():
    while True:
        try:
            await ws_manager.send_message("datos", await listaDatosOpc.conexionOpcPLC())
            await asyncio.sleep(10.0)
        except Exception as e:
            logger.error(f"Error en el lector del OPC: {e}")

async def central_opc_render_2():
    while True:
        try:
            await ws_manager.send_message("recetario", await listaRecetario.ConexionPLCRecetas())
            await asyncio.sleep(10.0)
        except Exception as e:
            logger.error(f"Error en el lector del OPC: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):       
    session = db.SessionLocal()
    try:
        if session.query(Usuario).count() == 0:
            usuario1 = Usuario(
                name = "creminox",
                role = "ADMIN",
                password = bcrypt_context.hash("1234")
            )
            usuario2 = Usuario(
                name = "efa-desmoldeo",
                role = "CLIENTE",
                password = bcrypt_context.hash("54321")
            )
            session.add_all([usuario1, usuario2])
            session.commit()
            logger.info("Base de datos inicializada con usuarios admin y cliente.")
        else:
            logger.info("Base de datos inicializada.")  

        if session.query(Alarma).count() == 0:
            logger.info(f"Cargar registros BDD [Alarmas]")
            cargar_archivo_sql(ruta_sql_alarmas)
        if session.query(Etapa).count() == 0:
            logger.info(f"Cargar registros BDD [Etapa]")
            cargar_archivo_sql(ruta_sql_etapas)
        if session.query(Recetario).count() == 0:
            logger.info(f"Cargar registros BDD [Recetario]")
            cargar_archivo_sql(ruta_sql_recetario)
        if session.query(Torre).count() == 0:
            logger.info(f"Cargar registros BDD [Torre]")
            cargar_archivo_sql(ruta_sql_torre)
        if session.query(TorreConfiguraciones).count() == 0:
            logger.info(f"Cargar registros BDD [TorreConfiguraciones]")

    except Exception as e:
        logger.error(f"Error al cargar diccionarios: {e}")
    try:
        await opc_client.connect()
        logger.info("Conectado al servidor OPC UA.")
        asyncio.create_task(central_opc_render())
        asyncio.create_task(central_opc_render_2())
        yield
    finally:
        await opc_client.disconnect()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas las solicitudes de cualquier dominio
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los headers
)

app.include_router(usuarios.RouterUsers)
app.include_router(graficosHistorico.RoutersGraficosH)
app.include_router(productividad.RouterProductividad)
@app.websocket("/ws/{id}")
async def resumen_desmoldeo(websocket: WebSocket, id: str):
    await websocket.accept()
    await ws_manager.connect(id, websocket)
    try:
        while True:
            await websocket.receive_json()  # Aquí puedes hacer validaciones si e
            await ws_manager.send_message(id, "data")
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        await ws_manager.disconnect(id, websocket)

@app.get("/")
def read_root():
        return {"nodo id": 2, "value": "Hola Mundo- Levanto el server!!!!!!!!!"}