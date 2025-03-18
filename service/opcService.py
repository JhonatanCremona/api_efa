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
                print(f"VALOR {child.get_value()} - Nombre {child.get_browse_name().Name}")
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

    def leerRecetaOpc(self, indice, nbreNodo, listaNodos):
        lista = {}
        try:
            root_node = self.conexion_servidor.get_objects_nodos()
            objects_node = root_node.get_child(["0:Objects"])
            server_interface_node = objects_node.get_child(["2:ServerInterfaces"])
            logger.info(f"Receta Node: {server_interface_node}")

            server_interface_1 = server_interface_node.get_child(["2:Server interface_1"])
            server_interface_2 = server_interface_node.get_child(["2:Server interface_2"])

            if not server_interface_1 or not server_interface_2:
                logger.error("No se encontraron los nodos 'Server interface_1' o 'Server interface_2'.")
                return lista

            namespace_index = server_interface_1.nodeid.NamespaceIndex

            try:
                nodos_disponibles = [child.get_browse_name().to_string() for child in server_interface_1.get_children()]
            except Exception as e:
                logger.error(f"Error al obtener la lista de nodos disponibles: {e}")

            try:
                # Obtener el objeto de receta desde el servidor OPC
                receta_obj = server_interface_2.get_child(["2:Receta"])

                # Obtener valores de configuración
                valores = {
                    "alto_de_molde": receta_obj.get_child(["2:ALTO_DE_MOLDE"]).get_value(),
                    "alto_de_producto": receta_obj.get_child(["2:ALTO_DE_PRODUCTO"]).get_value(),
                    "altura_ajuste": receta_obj.get_child(["2:ALTURA_AJUSTE"]).get_value(),
                    "altura_ajuste_n1": receta_obj.get_child(["2:ALTURA_AJUSTE_N1"]).get_value(),
                    "altura_de_bastidor": receta_obj.get_child(["2:ALTURA_DE_BASTIDOR"]).get_value(),
                    "altura_n1": receta_obj.get_child(["2:ALTURA_N1"]).get_value(),
                    "ancho_producto": receta_obj.get_child(["2:ANCHO_PRODUCTO"]).get_value(),
                    "cantidad_niveles": receta_obj.get_child(["2:CANTIDAD_NIVELES"]).get_value(),
                    "delta_entre_niveles": receta_obj.get_child(["2:DELTA_ENTRE_NIVELES"]).get_value(),
                    "largo_de_molde": receta_obj.get_child(["2:LARGO_DE_MOLDE"]).get_value(),
                    "largo_de_producto": receta_obj.get_child(["2:LARGO_DE_PRODUCTO"]).get_value(),
                    "moldes_por_nivel": receta_obj.get_child(["2:MOLDES_POR_NIVEL"]).get_value(),
                    "nombre": receta_obj.get_child(["2:NOMBRE"]).get_value(),
                    "numero_de_gripper": receta_obj.get_child(["2:NUMERO_DE_GRIPPER"]).get_value(),
                    "peso_del_producto": receta_obj.get_child(["2:PESO_DEL_PRODUCTO"]).get_value(),
                    "tipo_de_molde": receta_obj.get_child(["2:TIPO_DE_MOLDE"]).get_value(),
                    "receta_proxima": receta_obj.get_child(["2:receta_proxima"]).get_value(),
                    "torre_proxima": receta_obj.get_child(["2:torre_proxima"]).get_value(),
                }
                lista.update(valores)
            except Exception as e:
                logger.error(f"Error al obtener los valores de la receta: {e}")
                lista.update({"torre_proxima": None, "receta_proxima": None})

        except Exception as e:
            logger.error(f"Error en la lectura de la receta OPC: {e}")
        
        return lista

