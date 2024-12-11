
from opcua import Client  # type: ignore

# URL del servidor OPC UA
URL = "opc.tcp://192.168.10.120:4840"
def buscar_todos_los_nodos_por_ns(nodo, ns):
    """
    Busca recursivamente todos los nodos en el servidor OPC UA con un NodeId de un determinado espacio de nombres (ns).
    Devuelve una lista de diccionarios con el NodeId y su valor.
    """
    nodos_encontrados = []  # Lista para almacenar los nodos encontrados con sus valores

    try:
        # Si el nodo actual pertenece al espacio de nombres especificado, agregarlo a la lista
        if nodo.nodeid.namespace_index == ns:
            nodo_info = {
                "NodeId": nodo.nodeid.to_string(),
                "BrowseName": nodo.get_browse_name().Name,
                "Valor": nodo.get_value()
            }
            nodos_encontrados.append(nodo_info)

        # Recorrer los hijos del nodo actual
        for child in nodo.get_children():
            nodos_encontrados.extend(buscar_todos_los_nodos_por_ns(child, ns))  # Llamada recursiva

    except Exception as e:
        print(f"Error al explorar nodo: {e}")
    
    return nodos_encontrados

def obtener_datos_de_nodos(ruta_nodo, ns):
    """
    Obtiene todos los nodos con un determinado espacio de nombres (ns) y sus valores.
    """
    client = None
    try:
        # Conectar al servidor OPC UA
        client = Client(ruta_nodo)
        client.connect()
        print("Conectado al servidor OPC UA.")

        # Obtener el nodo raíz de los objetos
        objects = client.get_objects_node()

        # Buscar todos los nodos con el NodeId dentro del espacio de nombres (ns) proporcionado
        nodos = buscar_todos_los_nodos_por_ns(objects, ns)

        if not nodos:
            raise Exception(f"No se encontraron nodos con el espacio de nombres ns={ns}.")

        # Retornar los nodos encontrados con sus valores
        return nodos

    except Exception as e:
        print(f"Error al obtener nodos: {e}")
        return {"error": str(e)}

    finally:
        if client:
            try:
                client.disconnect()
                print("Cliente desconectado del servidor OPC UA.")
            except Exception as disconnect_error:
                print(f"Error durante la desconexión: {disconnect_error}")
