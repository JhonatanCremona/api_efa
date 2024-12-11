from typing import Union
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from config.opc import OPCUAClient, leer_nodo

URL = "opc.tcp://192.168.10.120:4840"
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
async def read_node():
    try:
        # Llama a la función leer_nodo con la ruta especificada
        nodo_info = leer_nodo(URL,i=22,cant=5,ns=4)
        
        # Verifica si la información del nodo es válida
        if nodo_info is None:
            raise HTTPException(status_code=404, detail="Nodo no encontrado")
        
        #return nodo_info
        return {"status": "success", "data": nodo_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer el nodo: {e}")
    


