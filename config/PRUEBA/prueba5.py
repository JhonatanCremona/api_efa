from opcua import Client
from datetime import datetime

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


def buscar_nodo_por_id(nodo, node_id):
    """
    Busca recursivamente un nodo específico en el servidor OPC UA utilizando su NodeId.
    """
    try:
        # Si el nodo actual coincide con el NodeId deseado, retorna el nodo
        if nodo.nodeid.to_string() == node_id:
            #print(f"Nodo encontrado: {nodo}, BrowseName: {nodo.get_browse_name()}")
            return nodo

        # Iterar sobre los hijos del nodo actual
        for child in nodo.get_children():
            resultado = buscar_nodo_por_id_iterativo(child, node_id)
            if resultado:  # Si se encuentra el nodo en algún hijo, retornarlo
                return resultado

    except Exception as e:
       
        return None


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
               # print(f"Nodo con ID {node_id} no encontrado.")
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




#main
# Conectar al servidor OPC UA y obtener los valores de todos los nodos en un namespace específico
URL="opc.tcp://192.168.10.120:4840"
i=22
cant=5
ns=4
resultados = leer_nodo(URL,i,cant,ns)

# Mostrar los resultados
if "error" in resultados:
    print(resultados["error"])
else:
    for resultado in resultados:
        print(f"Nodo: {resultado['nodo']}, Valor: {resultado['valor']}")
