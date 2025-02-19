from opcua import Client
import logging 
import time

logger = logging.getLogger("uvicorn")
class OPCUAClient:

    def __init__(self, server_url, max_retries=5, retry_delay=10):
        self.server_url = server_url
        self.client = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def connect(self):
        retries = 0
        while retries < self.max_retries:
            try:
                self.client = Client(self.server_url)
                self.client.connect()
                logger.info("Conectado al servidor OPC UA.")
                return
            except Exception as e:
                retries += 1
                logger.error(f"🔄 Error al conectar al servidor OPC UA. Intento {retries}/{self.max_retries}: {e}")
                time.sleep(self.retry_delay) 
        logger.warning("⚠️ No se pudo conectar al servidor después de varios intentos.")

    def disconnect(self):
        if self.client:
            self.client.disconnect()
            logger.warning("Conexión cerrada.")
            self.client = None

    def read_node(self, node_id):
        if not self.client:
            raise Exception("Cliente no conectado.")
        node = self.client.get_node(node_id)
        return node.get_value()
    
    def get_objects_node(self):
        if not self.client:
            raise Exception("Cliente no conectado.")
        return self.client.get_objects_node()
    def get_objects_nodos(self):
        return self.client.get_root_node()
