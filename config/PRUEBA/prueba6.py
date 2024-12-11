from opcua import Client

from queue import Queue

def buscar_nodo_por_id_iterativo(nodo_raiz, node_id):
    """
    Busca un nodo específico en el servidor OPC UA utilizando su NodeId con un enfoque iterativo.
    """
    try:
        # Inicializar una cola para los nodos pendientes de explorar
        cola = Queue()
        cola.put(nodo_raiz)

        while not cola.empty():
            # Obtener el siguiente nodo de la cola
            nodo_actual = cola.get()

            # Si el nodo actual coincide con el NodeId deseado, retornarlo
            if nodo_actual.nodeid.to_string() == node_id:
                return nodo_actual

            # Agregar los hijos del nodo actual a la cola
            for child in nodo_actual.get_children():
                cola.put(child)

    except Exception as e:
        print(f"Error al buscar nodo: {e}")

    # Si no se encuentra el nodo, retornar None
    return None




def buscar_nodo_por_id_una_vez(nodo_raiz, node_id_inicial, ns):
    """
    Busca un nodo específico en el servidor OPC UA utilizando su NodeId y retorna el nodo encontrado.
    """
    try:
        # Construir el NodeId completo
        node_id = f"ns={ns};i={node_id_inicial}"

        # Búsqueda inicial
        nodo_inicial = buscar_nodo_por_id_iterativo(nodo_raiz, node_id)
        if nodo_inicial:
            print(f"Nodo inicial encontrado: {nodo_inicial.get_browse_name()}")
        else:
            print(f"Nodo con ID {node_id} no encontrado.")
        return nodo_inicial

    except Exception as e:
        print(f"Error en la búsqueda inicial: {e}")
        return None




def leer_nodos_consecutivos(nodo_inicial, cantidad):
    """
    Lee los valores de una cantidad de nodos consecutivos a partir del nodo inicial.
    """
    resultados = []
    try:
        # Obtener todos los hijos del nodo inicial
        hijos = nodo_inicial.get_children()

        for i in range(cantidad):
            try:
                # Verificar si hay suficientes hijos
                if i >= len(hijos):
                    resultados.append({"nodo": f"{nodo_inicial.nodeid.to_string()} + {i}", "valor": "NULL"})
                    continue
                
                # Leer el valor del hijo actual
                nodo_actual = hijos[i]
                valor = nodo_actual.get_value()
                resultados.append({"nodo": nodo_actual.nodeid.to_string(), "valor": valor})

            except Exception as e:
                print(f"Error al leer nodo hijo {i}: {e}")
                resultados.append({"nodo": nodo_actual.nodeid.to_string() if nodo_actual else "NULL", "valor": "NULL"})

    except Exception as e:
        print(f"Error al iterar sobre nodos consecutivos: {e}")
    
    return resultados




ruta_nodo = "opc.tcp://192.168.10.120:4840"
ns = 4
node_id_inicial = 21
cantidad = 10

# Conectar al cliente OPC UA
client = Client(ruta_nodo)
client.connect()

# Obtener el nodo raíz
objects = client.get_objects_node()

# Buscar el nodo inicial
nodo_inicial = buscar_nodo_por_id_una_vez(objects, node_id_inicial, ns)

# Leer valores consecutivos
if nodo_inicial:
    resultados = leer_nodos_consecutivos(nodo_inicial, cantidad)
    for resultado in resultados:
        print(resultado)
else:
    print("No se pudo encontrar el nodo inicial.")

client.disconnect()