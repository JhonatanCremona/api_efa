from typing import Union
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import text
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
from models.usuario import Usuario
from models.torreconfiguraciones import TorreConfiguraciones

from routers import usuariosRouter, graficosHistorico, resumenProductividad, configuracionesHTTP
from service.configService import listarRecetas, listarTorres, obtenerTorre, datosRecetasConfiguraciones
from service.datosTiempoReal import datosGenerale, resumenEtapaDesmoldeo, datosResumenCelda
from service.alarmasService import enviarDatosAlarmas, enviaListaLogsAlarmas
from desp import bcrypt_context

import socket
import asyncio
import logging
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger("uvicorn")
localIp = socket.gethostbyname(socket.gethostname())
ruta_principal = os.path.dirname(os.path.abspath(__file__))

opc_ip = os.getenv("OPC_SERVER_IP")
opc_port = os.getenv("OPC_SERVER_PORT")

path_sql_alarma = os.getenv("PATH_QUERY_ALARMA_LAP")

ruta_sql = os.path.join(ruta_principal, 'query', 'insert_alarmas.sql')
ruta_sql_etapas = os.path.join(ruta_principal, 'query', 'etapas.sql')

password_admin = os.getenv("CREDENCIAL_SQL_USER_ADMIN")
password_cliente = os.getenv("CREDENCIAL_SQL_USER_CLIENT")
ultimo_estado = None 
ciclo_guardado = None
pesoActual = 0
ultimo_nivel = 0
#URL = f"opc.tcp://{opc_ip}:{opc_port}"
URL = f"opc.tcp://192.168.0.191:4841"
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
    global ultimo_estado, ciclo_guardado, pesoActual, ultimo_nivel
    while True:
        try:    
            
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

            if datosGenerales["PesoActualDesmoldado"] > 5 and datosGenerales["sdda_nivel_actual"] > ultimo_nivel:
                    ultimo_nivel = datosGenerales["sdda_nivel_actual"]
                    pesoActual = datosGenerales["PesoActualDesmoldado"] * 10 # PARCHE QUITAR EL X10 
                    
            if estado_actual != ultimo_estado:
                logger.info(f"ESTADO DEL CICLO {ultimo_estado}")
                
                if estado_actual == True:
                    logger.info("LLEGUE AL IF GUARDA DATOS")
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
                            cantidadNivelesFinalizado = ultimo_nivel, 
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
                            ciclo_actual.pesoDesmoldado = pesoActual
                            ciclo_actual.tiempoDesmolde = int((datetime.now() - ciclo_actual.fecha_inicio).total_seconds() // 60)
                            db_session.commit()
                            db_session.refresh(ciclo_actual)
                            logger.info(f"Ciclo actualizado con ID: {ciclo_actual.id}")
                            pesoActual = 0;
                            ultimo_nivel= 0;
                    except Exception as e:
                        db_session.rollback()
                        logger.error(f"Error al actualizar el ciclo: {e}")

            ultimo_estado = estado_actual
            
            await asyncio.sleep(3.0) 
        except Exception as e:
            db.rollback()
            logger.error(f"Error en el lector central del OPC: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    session = db.SessionLocal()
    try:
        if session.query(Usuario).count() == 0:
            usuario1 = Usuario(
                name = "creminox",
                role = "ADMIN",
                password = bcrypt_context.hash(password_admin)
            )
            usuario2 = Usuario(
                name = "cliente",
                role = "CLIENTE",
                password = bcrypt_context.hash(password_cliente)
            )
            session.add_all([usuario1, usuario2])
            session.commit()
            logger.info("Base de datos inicializada con usuarios admin y cliente.")
        else:
            logger.info("Base de datos inicializada.")
    except Exception as e:
        logger.error(f"Error inicializando la base de datos: {e}")
        raise e

    try:
        cargar_archivo_sql(ruta_sql_etapas)
        cargar_archivo_sql(ruta_sql)
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
app.include_router(configuracionesHTTP.RouterConfiguraciones)


@app.websocket("/ws/{id}")
async def resumen_desmoldeo(websocket: WebSocket, id: str):
    await websocket.accept()
    await ws_manager.connect(id, websocket)
    try:
        while True:
            await websocket.receive_json()  # Aquí puedes hacer validaciones si es necesario
            data = resumenEtapaDesmoldeo(opc_client)  #SE PUEDE ELIMINAR ?
            await ws_manager.send_message(id, data)
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        await ws_manager.disconnect(id, websocket)

@app.get("/")
def read_root():
        return "Hola Mundo"
