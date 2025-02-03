from opcua import Client

class OPCUAClient:

    def __init__(self, server_url):
        self.server_url = server_url
        self.client = None

    def connect(self):
        if not self.client:
            self.client = Client(self.server_url)
            self.client.connect()
            print("Conectado al servidor OPC UA.")

    def disconnect(self):
        if self.client:
            self.client.disconnect()
            print("Conexión cerrada.")
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
