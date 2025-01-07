from fastapi import APIRouter, HTTPException

from service.datosTiempoReal import datosGenerale, resumenEtapaDesmoldeo
from config.opc import OPCUAClient

import socket

localIp = socket.gethostbyname(socket.gethostname())
URL = f"opc.tcp://{localIp}:4840"
opc_client = OPCUAClient(URL)
opc_client.connect()

RouterLive = APIRouter(prefix="/dev", tags=["PruebaHTTPDatosOPC"], responses={404: {"description": "Sin Acceso al servidor OPC"}})

@RouterLive.get("/resumen-desmoldeo")
def read_resumen_desmoldeo():
    try:
        return resumenEtapaDesmoldeo(opc_client)
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al obtener el resumen desmoldeo: {e}")
@RouterLive.get("/lista-tiempo-real")
def read_lista_tiempo_real():
    try:
        return datosGenerale(opc_client)
    except Exception as e: 
        raise HTTPException(status=500, detail=f"Error al obtener la lista de datos tiempo real: {e}")
@RouterLive.get("/read")
async def readNode():
    try:
        value = opc_client.read_node(f"ns=2;i=2")
        return value
        
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al leer el nodo: {e}")