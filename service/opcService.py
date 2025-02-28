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
            logger.error(f"Error al buscar nodos ALARMA: {e}")
            
        return listaAlarma 

    def leerNodoAlarmaOpcVirtual(self, indice, nbreObjeto, nbreNodo):
        listaAlarma = []
        try:
            root_node = self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["2:ServerInterfaces"])
            server_interface_2 = server_interface_node.get_child(["2:Server interface_2"])
            alarmaArray = server_interface_2.get_child(["2:Alarma"])

            children = alarmaArray.get_children()

            listaAlarma = []
            for child in children:
                #print(f"VALOR {child.get_value()} - Nombre {child.get_browse_name().Name}")
                listaAlarma.append(child.get_value())

        except Exception as e:
                    logger.error(f"Error al buscar nodos ALARMA: {e}")
                    
        return listaAlarma

    def buscarNodoOpcVirtual(self, indice, nbreNodo, listaNodos):
        lista = {}
        try:
            root_node = self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["2:ServerInterfaces"])
            logger.info(f"Receta Node: {server_interface_node}")

            server_interface_1 = server_interface_node.get_child(["2:Server interface_1"])
            if not server_interface_1:
                logger.error("No se encontró 'Server interface_1'.")
                return lista

            # Obtener namespace index dinámicamente
            namespace_index = server_interface_1.nodeid.NamespaceIndex

            try:
                nodos_disponibles = [child.get_browse_name().to_string() for child in server_interface_1.get_children()]
            except Exception as e:
                logger.error(f"Error al obtener la lista de nodos disponibles: {e}")
                return lista

            for nodo in listaNodos:
                try:
                    nodo_path = f"{namespace_index}:{nodo}"

                    # Verifica si el nodo existe en la lista de hijos
                    if nodo_path not in nodos_disponibles:
                        logger.warning(f"El nodo '{nodo}' no existe en 'Server interface_1'.")
                        lista[nodo] = None
                        continue

                    # Obtener el nodo si existe
                    nodo_obj = server_interface_1.get_child([nodo_path])

                    # Intentar obtener el valor del nodo
                    try:
                        valor = nodo_obj.get_value()
                    except Exception as e:
                        logger.error(f"No se pudo obtener el valor del nodo {nodo}: {e}")
                        valor = None

                    # Interpretación de valores según el tipo de dato
                    if nodo == "desmoldeobanda":
                        lista[nodo] = "Banda A" if valor == 1 else "Banda B"
                    elif nodo == "estadoMaquina":
                        lista[nodo] = "Activo" if valor == 1 else "Inactivo" if valor == 2 else "Pausado"
                    else:
                        lista[nodo] = valor

                except Exception as e:
                    logger.error(f"Error al procesar el nodo {nodo} ({nodo_path}): {e}")
                    if "BadNoMatch" in str(e):
                        lista[nodo] = None  # Nodo no encontrado
                    else:
                        lista[nodo] = "Error"

            return lista

        except Exception as e:
            logger.error(f"Error al buscar nodos Lista valores: {e}")
            return lista

