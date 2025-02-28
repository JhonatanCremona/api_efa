from fastapi import WebSocket
from typing import Dict, Any, Set
import logging

logger = logging.getLogger("uvicorn")
TMessagePayload = Any
TActiveConnections = Dict[str, Set[WebSocket]]

class WSManager:
    def __init__(self):
        self.active_connections: TActiveConnections = {}

    async def connect(self, poll_id: str, ws: WebSocket):
        self.active_connections.setdefault(poll_id, set()).add(ws)

    async def disconnect(self, poll_id: str, ws: WebSocket):
        self.active_connections[poll_id].remove(ws)

    async def send_message(self, poll_id: str, message: list):
        if poll_id in self.active_connections:
            websockets = self.active_connections[poll_id]
            for websocket in websockets:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error al enviar mensaje a WebSocket: {e}")
        else:
            logger.info(f"No se encontró la conexión para poll_id: {poll_id}")

ws_manager = WSManager() 

























