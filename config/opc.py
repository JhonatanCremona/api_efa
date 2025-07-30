from opcua import Client
import logging
import asyncio

logger = logging.getLogger("uvicorn")

class OPCUAClient:
    def __init__(self, server_url, max_retries=3, retry_delay=5):
        self.server_url = server_url
        self.client = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connected = False  # Indicador de conexión

    async def connect(self):
        retries = 0
        while retries < self.max_retries:
            try:
                # Si no hay cliente o si está desconectado, creamos uno nuevo
                if self.client is None or not self.connected:
                    self.client = Client(self.server_url)
                    await asyncio.to_thread(self.client.connect)  # Conectar en un hilo de fondo
                    self.connected = True
                    logger.info("✅ Conectado al servidor OPC UA.")
                    return
            except Exception as e:
                retries += 1
                logger.error(f"🔄 Error al conectar al servidor OPC UA. Intento {retries}/{self.max_retries}: {e}")
                await asyncio.sleep(self.retry_delay) 
        logger.warning("⚠️ No se pudo conectar al servidor después de varios intentos.")

    async def disconnect(self):
        if self.client and self.connected:
            self.client.disconnect()
            logger.warning("⚠️ Conexión OPC UA cerrada.")
            self.connected = False
            self.client = None

    async def reconnect(self):
        """Intentar reconectar si la conexión se pierde"""
        logger.info("🔄 Intentando reconectar al servidor OPC UA...")
        await self.disconnect()  # Desconectar primero si hay conexión activa
        await self.connect()  # Volver a intentar conectar

    def read_node(self, node_id):
        if not self.client or not self.connected:
            raise Exception("⚠️ Cliente OPC UA no conectado.")
        node = self.client.get_node(node_id)
        return node.get_value()

    def get_objects_node(self):
        if not self.client or not self.connected:
            raise Exception("⚠️ Cliente OPC UA no conectado.")
        return self.client.get_objects_node()

    async def get_objects_nodos(self):
        if not self.client or not self.connected:
            raise Exception("⚠️ Cliente OPC UA no conectado.")
        return self.client.get_root_node()

    async def handle_reconnect(self):
        try:
            await self.reconnect()
        except Exception as e:
            logger.error(f"⚠️ Error al intentar reconectar: {e}")