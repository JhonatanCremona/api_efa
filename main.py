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
import os

ruta_principal = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger("uvicorn")
local_ip = socket.gethostbyname(socket.gethostname())

opc_ip = os.getenv("OPC_SERVER_IP")
opc_port = os.getenv("OPC_SERVER_PORT")

ruta_sql_alarmas = os.path.join(ruta_principal, 'query', 'insert_alarmas.sql')
ruta_sql_etapas = os.path.join(ruta_principal, 'query', 'insert_etapas.sql')
ruta_sql_recetario = os.path.join(ruta_principal, 'query', 'insert_recetario.sql')
ruta_sql_torre = os.path.join(ruta_principal,'query', 'insert_torre.sql')
ruta_sql_torre_configuraciones = os.path.join(ruta_principal,"query","insert_torre_configuraciones.sql")

ruta_sql_torre_ciclo = os.path.join(ruta_principal,"query","insert_ciclo_iffa.sql")
ruta_sql_torre_receta_ciclo = os.path.join(ruta_principal,"query","insert_recetaxciclo_iffa.sql")

#URL = f"opc.tcp://{local_ip}:4841"
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

def proceso_central_opc_alarmas(stop_event):
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
                await alarma_reader.leerAlarmasRobot()
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
        
        if session.query(CicloDesmoldeo).count() == 0:
            cargar_archivo_sql(ruta_sql_torre_ciclo)
            logger.info(f"Cargar registros BDD [CicloDesmoldeo]")
        if session.query(RecetarioXCiclo).count() == 0:
            cargar_archivo_sql(ruta_sql_torre_receta_ciclo)
            logger.info(f"Cargar registros BDD [RecetarioXCiclo]")
        

    except Exception as e:
        logger.error(f"Error al cargar diccionarios: {e}")
    try:
        await opc_client.connect()
        logger.info("Conectado al servidor OPC UA.")
        asyncio.create_task(central_opc_render_ws())

        #p1 = Process(target=proceso_central_opc_ws, daemon=True) // OMITIR
        p2 = Process(target=proceso_central_opc_escritura, args=(stop_event,),daemon=True)
        p3 = Process(target=proceso_central_opc_recetas, args=(stop_event,),daemon=True)
        p4 = Process(target=proceso_central_opc_alarmas,args=(stop_event,), daemon=True)

        #p1.start()
        
        #p2.start()
        #p3.start()
        #p4.start()
        yield
    finally:
        #p1.terminate()

        stop_event.set()
        time.sleep(1)  # Esperar a que se limpien los procesos
        p2.terminate()  # Como backup si no se cerraron
        p2.join(timeout=5)

        stop_event.set()
        time.sleep(1)  # Esperar a que se limpien los procesos
        p3.terminate()  # Como backup si no se cerraron
        p3.join(timeout=5)
        
        stop_event.set()
        time.sleep(1)  # Esperar a que se limpien los procesos
        p4.terminate()  # Como backup si no se cerraron
        p4.join(timeout=5)
        await opc_client.disconnect()

app = FastAPI(
    lifespan=lifespan,
    )
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
app.include_router(configuracionesHTTP.RouterConfiguraciones)
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