from opcua import Client  # type: ignore

# URL del servidor OPC UA
URL = "opc.tcp://192.168.10.120:4840"

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
   

def leer_nodo(ruta_nodo, node_id):
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

    

# Llamada principal
if __name__ == "__main__":
    print("Iniciando lectura del nodo...")
    # Asegúrate de que el NodeId sea correcto
    resultado = leer_nodo(URL, node_id="ns=4;i=25")  # Cambia el NodeId según sea necesario
    print("Resultado:", resultado)