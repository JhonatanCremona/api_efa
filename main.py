from typing import Union
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from config.opc import OPCUAClient

URL = "opc.tcp://192.168.0.150:4840"
opc_client = OPCUAClient(URL)

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
        value = opc_client.read_node(f"ns=2;i=3")
        return {"nodo id": 2, "value": value}
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al leer el nodo: {e}")
