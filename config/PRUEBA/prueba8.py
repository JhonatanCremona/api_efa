from opcua import Client
from queue import Queue
from opcua import ua

def buscar_nodo_por_id_iterativo(nodo_raiz, node_id):
    """
    Busca un nodo específico en el servidor OPC UA utilizando su NodeId con un enfoque iterativo.
    """
    try:
        cola = Queue()
        cola.put(nodo_raiz)

        while not cola.empty():
            nodo_actual = cola.get()

            if nodo_actual.nodeid.to_string() == node_id:
                return nodo_actual

            try:
                for child in nodo_actual.get_children():
                    cola.put(child)
            except Exception as e:
                print(f"Error al obtener hijos de {nodo_actual}: {e}")
    except Exception as e:
        print(f"Error al buscar nodo: {e}")
    return None


def buscar_nodo_por_id_una_vez(nodo_raiz, node_id_inicial, ns):
    """
    Busca un nodo específico en el servidor OPC UA utilizando su NodeId y retorna el nodo encontrado.
    """
    node_id = f"ns={ns};i={node_id_inicial}"
    nodo = buscar_nodo_por_id_iterativo(nodo_raiz, node_id)

    if nodo:
        print(f"Nodo inicial encontrado: {nodo.get_browse_name()}")
    else:
        print(f"Nodo con ID {node_id} no encontrado.")
    return nodo


def leer_nodos_consecutivos_1(nodo_inicial, cantidad):
    """
    Lee los valores de una cantidad de nodos consecutivos a partir del nodo inicial.
    """
    resultados = []
    try:
        hijos = nodo_inicial.get_children()
        for i in range(cantidad):
            if i >= len(hijos):
                resultados.append({"nodo": "NULL", "valor": "NULL"})
                continue

            nodo_actual = hijos[i]
            try:
                valor = nodo_actual.get_value()
                resultados.append({"nodo": nodo_actual.nodeid.to_string(), "valor": valor})
            except Exception as e:
                print(f"Error al leer valor del nodo {nodo_actual}: {e}")
                resultados.append({"nodo": nodo_actual.nodeid.to_string(), "valor": "ERROR"})
    except Exception as e:
        print(f"Error al iterar sobre hijos del nodo: {e}")
    return resultados


def leer_nodos_consecutivos(nodo_inicial, cantidad):
    """
    Lee los valores de una cantidad de nodos consecutivos a partir del nodo inicial,
    explorando subcarpetas si es necesario.
    """
    resultados = []
    try:
        cola = [nodo_inicial]  # Usamos una cola para explorar los nodos y sus hijos
        nodos_leidos = 0  # Contador para asegurarse de que leemos la cantidad deseada de nodos

        while cola and nodos_leidos < cantidad:
            nodo_actual = cola.pop(0)  # Extraemos el siguiente nodo de la cola

            try:
                # Leer el valor del nodo actual
                valor = nodo_actual.get_value()
                resultados.append({"nodo": nodo_actual.nodeid.to_string(), "valor": valor})
                nodos_leidos += 1  # Contamos el nodo leído

                # Si el nodo tiene hijos, los agregamos a la cola para seguir explorando
                hijos = nodo_actual.get_children()
                if hijos:
                    cola.extend(hijos)

            except Exception as e:
                print(f"Error al leer valor del nodo {nodo_actual}: {e}")
                resultados.append({"nodo": nodo_actual.nodeid.to_string(), "valor": "ERROR"})

        # Si no hemos leído la cantidad completa de nodos, agregar nodos "NULL"
        while nodos_leidos < cantidad:
            resultados.append({"nodo": "NULL", "valor": "NULL"})
            nodos_leidos += 1

    except Exception as e:
        print(f"Error al iterar sobre los nodos: {e}")

    return resultados



def leer_nodos_consecutivos_con_subcarpetas(nodo_inicial, cantidad):
    """
    Lee los valores de una cantidad de nodos consecutivos a partir del nodo inicial,
    manejando subcarpetas cuando sea necesario.
    """
    resultados = []
    try:
        nodo_actual = nodo_inicial
        for i in range(cantidad):
            if nodo_actual is None:
                resultados.append({"nodo": f"{nodo_inicial.nodeid.to_string()} + {i}", "valor": "NULL"})
                break

            try:
                # Verificar si el nodo es un ExtensionObject
                valor = nodo_actual.get_value()
                if isinstance(valor, ua):
                    # Manejar ExtensionObject, por ejemplo, extrayendo sus atributos
                    resultados.append({"nodo": nodo_actual.nodeid.to_string(), "valor": f"ExtensionObject - {valor.TypeId}"})
                else:
                    # Si es un valor simple, añadirlo directamente
                    resultados.append({"nodo": nodo_actual.nodeid.to_string(), "valor": valor})

                # Obtener hijos del nodo actual
                hijos = nodo_actual.get_children()
                if hijos:  # Si el nodo tiene hijos, seguir con el primero
                    nodo_actual = hijos[0]
                else:
                    # Si no hay hijos, intentar avanzar al siguiente nodo en el mismo nivel
                    nodo_actual = None  # Este paso se ajusta si necesitas avanzar de nivel

            except Exception as e:
                print(f"Error al leer nodo: {e}")
                resultados.append({"nodo": nodo_actual.nodeid.to_string() if nodo_actual else "NULL", "valor": "NULL"})
                break

    except Exception as e:
        print(f"Error al iterar sobre nodos consecutivos: {e}")
    
    return resultados


# Configuración
ruta_nodo = "opc.tcp://192.168.10.120:4840"
ns = 4
node_id_inicial = 21
cantidad = 10

try:
    # Conectar al cliente OPC UA
    client = Client(ruta_nodo)
    client.connect()
    print("Conexión establecida con el servidor OPC UA.")

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
except Exception as e:
    print(f"Error durante la ejecución: {e}")
finally:
    # Desconectar el cliente
    client.disconnect()
    print("Desconexión del cliente OPC UA.")
