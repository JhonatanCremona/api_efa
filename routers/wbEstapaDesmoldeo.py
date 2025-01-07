from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from config.ws import ws_manager

from config.opc import OPCUAClient

from service.datosTiempoReal import resumenEtapaDesmoldeo

import socket
import asyncio

localIp = socket.gethostbyname(socket.gethostname())
URL = f"opc.tcp://{localIp}:4840"
opc_client = OPCUAClient(URL)

router = APIRouter(prefix="/ws", tags=["DatosEnTiempoReal"], responses={404: {"description": "Not Found"}})

