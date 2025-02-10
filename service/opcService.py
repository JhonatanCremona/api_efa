from opcua import Client
import logging

logger = logging.getLogger("uvicorn")
class ObtenerNodosOpc:
    def __init__(self, conexion_servidor):
        self.conexion_servidor = conexion_servidor
    
    def buscarNodos(self, indice, nbreObjeto, listaNodos):
        lista = {}
        try:
            #root_node = self.conexion_servidor.get_objects_node()
            root_node = self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["3:ServerInterfaces"])
            receta_node = server_interface_node.get_child([f"{indice}:{nbreObjeto}"])

            logger.info(f"Conectado al servidor. Nodo raíz: {root_node}")
            
            #DESARROLLO CON SERVER VIRTUAL
            #receta_node = root_node.get_child(["2:Server interface_1"])
            
            for nodo in listaNodos:
                try:
                    nodo_obj = receta_node.get_child([f"{indice}:{nodo}"])
                    if nodo_obj == "desmoldeobanda":
                        lista[nodo] = "Banda A" if nodo_obj.get_value() == 1 else "Banda B"
                    elif nodo_obj == "estadoMaquina":
                        lista[nodo] = "Activo" if nodo_obj.get_value() == 1 else "Inactivo" if nodo_obj.get_value() == 2 else "Pausado"
                    else:
                        lista[nodo] = nodo_obj.get_value()

                except Exception as e:
                    logger.error(f"Error al obtener el nodo {nodo}: {e}")
                    if "BadNoMatch" in str(e):
                        lista[nodo] = 0 

            return lista
        
        except Exception as e:
            logger.error(f"Error al buscar nodos: {e}")
            
        return lista
        
    def leerNodoAlarma(self, indice, nbreObjeto, nbreNodo):
        listaAlarma = []
        try:
            root_node = self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["3:ServerInterfaces"])
            receta_node = server_interface_node.get_child([f"{indice}:{nbreObjeto}"])
            alarmaArray = receta_node.get_child([f"{indice}:{nbreNodo}"])
            children = alarmaArray.get_children()
            for child in children:
                listaAlarma.append(child.get_value())
            return listaAlarma

        except Exception as e:
            logger.error(f"Error al buscar nodos: {e}")
            
        return listaAlarma 

    #ELIMINAR METODO
    def buscarNodo(self, indice, nbreObjeto, nbreNodo):
        try:

            root_node = self.conexion_servidor.get_objects_nodos()
            #listaNodos = root_node.get_child(["0:Objects", "2:Server interface_2"])
            
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["3:ServerInterfaces"])
            receta_node = server_interface_node.get_child(["5:Server interface_2"])

            nodo = receta_node.get_child(f"{indice}:{nbreNodo}")
            return nodo.get_value()
        except Exception as e:
            print(f"Error al buscar el nodo: {e}")
            return None