from opcua import Client
class Recetas:
    def __init__(self, conexion_servidor):
        self.conexion_servidor = conexion_servidor
    
    def buscarNodos(self, indice, nbreObjeto, listaNodos):
        lista = {}
        try:
            root_node = self.conexion_servidor.get_objects_node()
            print(f"Conectado al servidor. Nodo raíz: {root_node}")

            receta_node = root_node.get_child([f"{indice}:{nbreObjeto}"])
            print(f"Nodo receta encontrado: {receta_node}")

            for nodo in listaNodos:
                try:
                    nodo_obj = receta_node.get_child([f"{indice}:{nodo}"])
                    lista[nodo] = nodo_obj.get_value()
                    print(f"Valor del nodo {nodo}: {lista[nodo]}")

                except Exception as e:
                    print(f"Error al obtener el nodo {nodo}: {e}")
                    if "BadNoMatch" in str(e):
                        lista[nodo] = 0

            return lista


        except Exception as e:
            print(f"Error al buscar nodos: {e}")
            return None    
        