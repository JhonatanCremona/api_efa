from typing import Union
from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager
from config.opc import OPCUAClient

from models.receta import Recetas
from service.datosTiempoReal import datosGenerale, resumenEtapaDesmoldeo

from sqlalchemy.orm import Session
from service.useriosService import get_listaUsuarios
from config import db

from models.ciclo import Ciclo 
from models.etapa import Etapa
from models.torre import Torre
from models.recetaxciclo import RecetaXCiclo
from models.alarma import Alarma
from models.kuka import Kuka
from models.sdda import Sdda

import socket

localIp = socket.gethostbyname(socket.gethostname())

URL = f"opc.tcp://{localIp}:4840"
opc_client = OPCUAClient(URL)

db.Base.metadata.drop_all(bind=db.engine)
db.Base.metadata.create_all(bind=db.engine)

# INSERT INTO usuarios(name, password) VALUES ("cliente", "1234");
# INSERT INTO usuarios(name, password) VALUES ("creminox", "12345");

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        opc_client.connect()
        yield
    finally:
        opc_client.disconnect()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/read")
async def readNode():
    try:
        value = opc_client.read_node(f"ns=2;i=2")
        return {"nodo id": 2, "value": value}
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al leer el nodo: {e}")
    
    
@app.get("/desarrollo/datosgenerales")
def read_lista_datos_generales():
    listaDGenerales = {}
    try:
        receta = Recetas(opc_client)
        indice = 2
        nbreObjeto = "datosGripper"

    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al obener datos General: {e}")    
    
@app.get("/desarrollo/lista-usuarios")
def read_lista_usuarios(skip: int = 0, limit: int = 10, db: Session = Depends(db.get_db)):
    users = get_listaUsuarios(db, skip=skip, limit=limit)
    return users

@app.get("/desarrollo/lista-tiempo-real")
def read_lista_tiempo_real():
    try:
        return datosGenerale(opc_client)
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al obtener la lista de datos tiempo real: {e}")
    finally:
        opc_client.disconnect()

@app.get("/desarrollo/resumen-desmoldeo")
def read_resumen_desmoldeo():
    try:
        return resumenEtapaDesmoldeo(opc_client)
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al obtener el resumen desmoldeo: {e}")
    finally:
        opc_client.disconnect()

