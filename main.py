from typing import Union
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import text
from multiprocessing import Process, cpu_count, Event


from config.opc import OPCUAClient
from config import db
from config.ws import ws_manager
from services.opcService import ObtenerNodosOpc
from services.opcRecetas import OpcRecetas

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
from routers import usuarios, graficosHistorico, productividad, configuracionesHTTP

import logging
import asyncio
import time
import socket

from dotenv import load_dotenv
from config.logger_config import logger
import os

from email_utils import tarea_exportar_y_enviar

logger = logging.getLogger("uvicorn")
ruta_principal = os.path.dirname(os.path.abspath(__file__))

local_ip = socket.gethostbyname(socket.gethostname())

opc_ip = os.getenv("OPC_SERVER_IP")
opc_port = os.getenv("OPC_SERVER_PORT")

ruta_sql_alarmas = os.path.join(ruta_principal, 'query', 'insert_alarmas.sql')
ruta_sql_etapas = os.path.join(ruta_principal, 'query', 'insert_etapas.sql')
ruta_sql_recetario = os.path.join(ruta_principal, 'query', 'insert_recetario.sql')
ruta_sql_torre = os.path.join(ruta_principal,'query', 'insert_torre.sql')
ruta_sql_torre_configuraciones = os.path.join(ruta_principal,"query","insert_torre_configuraciones.sql")

URL = f"opc.tcp://{opc_ip}:{opc_port}"
opc_client = OPCUAClient(URL)

#db.Base.metadata.drop_all(bind=db.engine)
db.Base.metadata.create_all(bind=db.engine)

listaDatosOpc = ObtenerNodosOpc(opc_client)

listaRecetario = ObtenerNodosOpc(opc_client)

actualizarRecetas = OpcRecetas(opc_client)

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

stop_event = Event()

async def central_opc_render_ws():
        while True:
            try:
                data = await listaDatosOpc.conexionOpcPLC()
                await ws_manager.send_message("datos", data)
                await asyncio.sleep(2.0)
            except Exception as e:
                logger.error(f"Error en el lector del OPC (lectura datos): {e}")

def proceso_central_opc_escritura(stop_event):
    from services.opcService import ObtenerNodosOpc
    from config.ws import ws_manager  # Importar dentro del proceso si es necesario

    client = OPCUAClient(URL)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(client.connect())
    listaRecetario = ObtenerNodosOpc(client)

    async def central_opc_render_torre_config():
        while not stop_event.is_set():
            try:
                inicio = time.time()
                data = await listaRecetario.ConexionPLCRecetas()
                fin = time.time()

                duracion = fin - inicio

                minutos = int(duracion // 60)
                segundos = int(duracion % 60)

                print(f"⏱ [UPDATE TORRE CONF.] Tiempo de ejecución: {minutos} minutos y {segundos} segundos")
                await ws_manager.send_message("lista-receta", data)
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error en el lector [Recetario TORRES] del OPC: {e}")

    try:
        loop.run_until_complete(central_opc_render_torre_config())
    finally:
        loop.run_until_complete(client.disconnect())
        loop.close()

def proceso_central_opc_recetas(stop_event):
    from services.opcRecetas import OpcRecetas  # Asegurate de que esté en un módulo separado

    client = OPCUAClient(URL)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(client.connect())
    receta_reader = OpcRecetas(client)

    async def central_opc_recetas():
        while not stop_event.is_set():
            try:
                inicio = time.time()
                await receta_reader.actualizarRecetas()
                fin = time.time()

                duracion = fin - inicio

                minutos = int(duracion // 60)
                segundos = int(duracion % 60)

                print(f"⏱ [UPDATE RECETAS] Tiempo de ejecución: {minutos} minutos y {segundos} segundos")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error en render recetas: {e}")

    try:
        loop.run_until_complete(central_opc_recetas())
    finally:
        loop.run_until_complete(client.disconnect())
        loop.close()


def proceso_central_opc_alarmas_2(stop_event):
    from services.opcAlarmas import OpcAlarmas

    client = OPCUAClient(URL)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(client.connect())
    alarma_reader = OpcAlarmas(client)
    async def central_opc_alarmas():
        while not stop_event.is_set():
            try:
                inicio = time.time()
                alarma_reader.leerAlarmasCeldaDesmoldeo()
                fin = time.time()

                duracion = fin - inicio

                minutos = int(duracion // 60)
                segundos = int(duracion % 60)

                print(f"⏱ [UPDATE ALARMAS] Tiempo de ejecución: {minutos} minutos y {segundos} segundos")

                await asyncio.sleep(5)
            except Exception as e:
                logger.warning(f"Error en el render alarmas: {e}")
    try:
        loop.run_until_complete(central_opc_alarmas())
    finally:
        loop.run_until_complete(client.disconnect())
        loop.close()

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
            cargar_archivo_sql(ruta_sql_torre_configuraciones)
            logger.info(f"Cargar registros BDD [TorreConfiguraciones]")
        
    except Exception as e:
        logger.error(f"Error al cargar diccionarios: {e}")
    try:
        await opc_client.connect()
        logger.info("Conectado al servidor OPC UA.")
        asyncio.create_task(central_opc_render_ws())
        asyncio.create_task(tarea_exportar_y_enviar())

        p2 = Process(target=proceso_central_opc_escritura, args=(stop_event,),daemon=True)
        p3 = Process(target=proceso_central_opc_recetas, args=(stop_event,),daemon=True)
        p4 = Process(target=proceso_central_opc_alarmas_2,args=(stop_event,), daemon=True)

        #PARA FRENAR UN PROCESO SOLO FRENAR ESTAS LINEAS

        #p1.start()
        #p2.start()
        #p3.start()
        #p4.start()

        yield
        
    finally:

        stop_event.set()
        time.sleep(1)
        p2.terminate()
        p2.join(timeout=5)

        stop_event.set()
        time.sleep(1)
        p3.terminate()
        p3.join(timeout=5)
        
        stop_event.set()
        time.sleep(1)
        p4.terminate()
        p4.join(timeout=5)

        await opc_client.disconnect()

app = FastAPI(
    lifespan=lifespan,
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(usuarios.RouterUsers)
app.include_router(graficosHistorico.RoutersGraficosH)
app.include_router(productividad.RouterProductividad)
app.include_router(configuracionesHTTP.RouterConfiguraciones)

@app.websocket("/ws/{id}")
async def resumen_desmoldeo(websocket: WebSocket, id: str):
    await websocket.accept()
    await ws_manager.connect(id, websocket)
    try:
        while True:
            await websocket.receive_json()
            await ws_manager.send_message(id, "data")
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        await ws_manager.disconnect(id, websocket)

@app.get("/")
def read_root():
    try:
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        estado_bdd = "Conectado"
    except Exception as e:
        estado_bdd = "Desconectado"
    
    try:
        if opc_client.connected and opc_client.client:
            root_node = opc_client.client.get_root_node()
            root_node.get_browse_name()
            estado_opc = "Conectado"
        else:
            estado_opc = "Desconectado"
    except Exception as e:
        estado_opc = "Desconectado"
    
    return {
        "nodo id": 2, 
        "value": "Hola Mundo- Levanto el server!", 
        "Estado BDD": estado_bdd, 
        "Estado OPC": estado_opc
    }