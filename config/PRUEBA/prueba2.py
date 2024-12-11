from opcua import Client, ua

# URL del servidor OPC UA
URL = "opc.tcp://192.168.10.120:4840"

def leer_nodo(ruta_servidor, namespace, id_nodo):
    """
    Conecta al servidor OPC UA, busca y lee el valor de un nodo específico usando el NodeId de la forma ns={namespace};i={id_nodo}.
    """
    client = None
    try:
        # Crear el NodeId con el namespace y el id proporcionado
        node_id = ua.NodeId(id_nodo, namespace)

        # Inicializar cliente y conectar al servidor
        client = Client(ruta_servidor)
        client.set_timeout(10_000)  # Configurar un timeout razonable
        client.connect()
        print("Conectado al servidor OPC UA.")

        # Obtener el nodo directamente por su NodeId
        nodo = client.get_node(node_id)

        if nodo is None:
            raise ValueError(f"Nodo con ID {node_id} no encontrado en el servidor OPC UA.")

        # Leer el valor del nodo
        valor = nodo.get_value()
        print(f"Valor del nodo {node_id}: {valor}")

        return {"nodo": node_id, "valor": valor}

    except Exception as e:
        print(f"Error al leer el nodo: {e}")
        return {"error": str(e)}

    finally:
        if client:
            try:
                client.disconnect()
                print("Cliente desconectado del servidor OPC UA.")
            except Exception as disconnect_error:
                print(f"Error durante la desconexión: {disconnect_error}")


# Llamada principal
if __name__ == "__main__":
    print("Iniciando lectura del nodo...")
    # Usamos los valores del namespace y el id del NodeId
    resultado = leer_nodo(URL, namespace=4, id_nodo=25)
    print("Resultado:", resultado)
