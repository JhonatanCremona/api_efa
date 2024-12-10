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

    #def read_node(self, node_id):
     #   if not self.client:
      #      raise Exception("Cliente no conectado.")
       # node = self.client.get_node(node_id)
        #return node.get_value()



def leer_nodo(ruta_nodo):
# Obtener el nodo raíz de los objetos
       
        client = Client(ruta_nodo)
        client.connect()
        objects = client.get_objects_node()

        # Navegar hacia el objeto INTERFACE (espacio de nombres NS=3)
        interface = objects.get_child(["3:ServerInterfaces"])
        MINI_PC = interface.get_child(["4:MINI PC"])
        # Navegar hacia el objeto LABORATORIO dentro de INTERFACE (espacio de nombres N2=4)
        laboratorio = MINI_PC.get_child(["4:LABORATORIO"])

        # Leer el valor de la variable dentro de LABORATORIO (espacio de nombres N2=4)
        variable = laboratorio.get_child(["4:NRO_RECETAS"])  # Cambia N2 por el nombre de la variable que deseas leer
        # Obtener el valor de la variable
        value = variable.get_value()
        # print(f"Valor de la variable: {value}")
        return value