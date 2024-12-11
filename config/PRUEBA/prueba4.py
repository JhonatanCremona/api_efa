from opcua import Client

def buscar_todos_los_nodos_por_ns(nodo, ns):
    """
    Busca recursivamente todos los nodos en el servidor OPC UA con un NodeId de un determinado espacio de nombres (ns).
    Devuelve una lista de diccionarios con el NodeId y su valor.
    """
    nodos_encontrados = []  # Lista para almacenar los nodos encontrados con sus valores

    try:
        # Comprobar si el nodo tiene el atributo 'namespace_index'
        if hasattr(nodo.nodeid, 'namespace_index') and nodo.nodeid.namespace_index == ns:
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

        # Mostrar por consola los nodos encontrados
        print("\nNodos encontrados:")
        for nodo in nodos:
            print(f"NodeId: {nodo['NodeId']}, BrowseName: {nodo['BrowseName']}, Valor: {nodo['Valor']}")

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

# Función principal para ejecutar el script
if __name__ == "__main__":
    # Definir la URL del servidor OPC UA y el espacio de nombres (ns)
    ruta_nodo  = "opc.tcp://192.168.10.120:4840"  # Cambiar esta URL al servidor correcto
    ns = 4  # Cambiar por el espacio de nombres (ns) que deseas explorar

    # Llamar a la función para obtener y mostrar los nodos
    obtener_datos_de_nodos(ruta_nodo, ns)
