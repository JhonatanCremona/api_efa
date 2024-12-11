from opcua import Client
from datetime import datetime
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



def leer_nodoa(ruta_nodo):
# Obtener el nodo raíz de los objetos
       
        client = Client(ruta_nodo)
        client.connect()
        objects = client.get_objects_node()

        # Navegar hacia el objeto INTERFACE (espacio de nombres NS=3)
        interface = objects.get_child(["3:ServerInterfaces"])
        MINI_PC = interface.get_child(["4:MINI PC"])
        # Navegar hacia el objeto LABORATORIO dentro de INTERFACE (espacio de nombres N2=4)
        laboratorio = MINI_PC.get_child(["4:LABORATORIO"])
        EQUIPO = laboratorio.get_child(["4:EQUIPO"])
        # Leer el valor del nodo 'NRO_RECETAS' en el espacio de nombres 4
        variable = EQUIPO.get_child(["4:NRO_RECETAS"])
        # Leer el valor de la variable dentro de LABORATORIO (espacio de nombres N2=4)
        
        # Obtener el valor de la variable
       
        valor = variable.get_value()

        return {"nodo": "NRO_RECETAS", "valor": valor}
        # print(f"Valor de la variable: {value}")
       


def buscar_nodo_por_id(nodo, node_id):
    """
    Busca recursivamente un nodo específico en el servidor OPC UA utilizando su NodeId.
    """
    try:
        # Si el nodo actual coincide con el NodeId deseado, retorna el nodo
        if nodo.nodeid.to_string() == node_id:
            print(f"Nodo encontrado: {nodo}, BrowseName: {nodo.get_browse_name()}")
            return nodo

        # Iterar sobre los hijos del nodo actual
        for child in nodo.get_children():
            resultado = buscar_nodo_por_id(child, node_id)
            if resultado:  # Si se encuentra el nodo en algún hijo, retornarlo
                return resultado

    except Exception as e:
       
        return None

    # Si no se encuentra el nodo, retornar None
   

def leer_nodos(ruta_nodo, node_id):
    """
    Lee el valor de un nodo específico en el servidor OPC UA dado su NodeId.
    """
    client = None
    try:
        # Conectar al servidor OPC UA
        client = Client(ruta_nodo)
        client.connect()
        print("Conectado al servidor OPC UA.")

        # Obtener el nodo raíz de los objetos
        objects = client.get_objects_node()

        # Buscar el nodo con el NodeId especificado
        nodo_deseado = buscar_nodo_por_id(objects, node_id)

        if nodo_deseado is None:
            raise Exception(f"Nodo con ID {node_id} no encontrado.")
         

        # Leer el valor del nodo encontrado
        valor = nodo_deseado.get_value()
    
        # Retornar el valor leído
        return {"nodo": node_id, "valor": valor}
    except Exception as e:
        return {"error": str(e)}    


def leer_nodo(ruta_nodo_, node_id_inicial, cantidad_nodos, NSpace):
    """
    Lee los valores de nodos de manera iterativa, sumando uno al NodeId en cada iteración
    y guardando los resultados en un arreglo.
    """
    client = None
    resultados = []  # Lista para almacenar los resultados
    
    try:
        # Conectar al servidor OPC UA
        client = Client(ruta_nodo_)
        client.connect()
        print("Conectado al servidor OPC UA.")

        # Obtener el nodo raíz de los objetos
        objects = client.get_objects_node()

        # Iterar sobre los nodos
        for i in range(cantidad_nodos):
            # Generar el NodeId para el nodo actual sumando uno al node_id_inicial
            node_id = f"ns={NSpace};i={node_id_inicial + i}"

            # Buscar el nodo con el NodeId generado
            nodo_deseado = buscar_nodo_por_id(objects, node_id)

            if nodo_deseado is None:
                print(f"Nodo con ID {node_id} no encontrado.")
                resultados.append({"nodo": node_id, "valor": "NULL", "tiempo": datetime.now()})
                continue
            
            # Leer el valor del nodo
            try:
                valor = nodo_deseado.get_value()
                resultados.append({"nodo": node_id, "valor": valor, "tiempo": datetime.now()})
            except Exception as e:
                print(f"Error leyendo el nodo {node_id}: {str(e)}")
                resultados.append({"nodo": node_id, "valor": "NULL", "tiempo": datetime.now()})

        # Retornar los resultados
        return resultados
    
    except Exception as e:
        return {"error": str(e)}
    
