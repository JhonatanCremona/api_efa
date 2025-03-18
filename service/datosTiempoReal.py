from service.opcService import ObtenerNodosOpc
from fastapi import HTTPException
from datetime import datetime
from config.db import get_db
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_
from models.ciclo import Ciclo
from models.torre import Torre
from models.recetaxciclo import Recetario
from opcua import Client
import logging

logger = logging.getLogger("uvicorn")

nbreObjeto = "Server interface_1"
nbreObjeto2 = "Server interface_2"
indice = 4
ulEstado = None
tiempoCiclo = "00:00 mm:ss"
fechaInicioCIclo = 0
def obtenerTiempo(estadoCiclo):
    global tiempoCiclo, fechaInicioCIclo, ulEstado

    if estadoCiclo != ulEstado:
        if estadoCiclo:
            fechaInicioCIclo = datetime.now()
            ulEstado = estadoCiclo
    elif estadoCiclo:
        transcurrido = datetime.now() - fechaInicioCIclo
        transcurrido = datetime.now() - fechaInicioCIclo
        minutos = transcurrido.seconds // 60
        segundos = transcurrido.seconds % 60
        tiempoCiclo = f"{minutos:02}:{segundos:02} mm:ss"
        
    if estadoCiclo == False:
        tiempoCiclo = 0
        fechaInicioCIclo = 0
        ulEstado = None
    
    return tiempoCiclo
def resumenEtapaDesmoldeo(opc_cliente):
    try:
        dResumenDatos = ObtenerNodosOpc(opc_cliente)
        diccinario = ["Nombre actual","idRecetaActual", "idRecetaProxima", "PesoProducto", "TotalNiveles", "TipoMolde", "estadoMaquina","desmoldeobanda", "sdda_nivel_actual", "iniciado", "finalizado", "torreActual", "cicloTiempoTotal", "NGripperActual"]
        resultado = dResumenDatos.buscarNodoOpcVirtual(indice,nbreObjeto, diccinario)
        resultado["estadoMaquina"] = "Activo" if resultado.get("estadoMaquina") == 1 else "Inactivo" if resultado.get("estadoMaquina") == 2 else "Pausado"
        resultado["TiempoTranscurrido"] = obtenerTiempo(resultado.get("iniciado"))
        resultado["PesoActualDesmoldado"] = resultado.get("PesoProducto") * resultado.get("sdda_nivel_actual")
        return resultado
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al obtener la lista de nodos: {e}")

def conversorListaAVectores(lista):
    return list(lista.values())

def obtenerLista(dGeneral, nivel, objeto, diccionario):
    return dGeneral.buscarNodoOpcVirtual(nivel, objeto, diccionario)

def datosGenerale(opc_cliente):
    try:
        dGeneral = ObtenerNodosOpc(opc_cliente)
        nodos = {
            "datosGripper": (nbreObjeto, ["NGripperActual", "NGripperProximo"]),
            "datosRobot": (nbreObjeto, ["posicionX", "posicionY", "posicionZ"]),
            "datosTorre": (nbreObjeto, [ "torreActual","torreProxima", "sdda_nivel_actual"]),
            "sectorIO": (nbreObjeto, ["estadoMaquina","desmoldeobanda"]),
            "datosSdda": (nbreObjeto, ["TotalNiveles", "sdda_long_mm","sdda_vertical_mm"]),
        }
        listaDatosTiempoReal = {
            clave: conversorListaAVectores(obtenerLista(dGeneral, indice, objeto, diccionario)) for clave, (objeto, diccionario) in nodos.items()
        }
        return listaDatosTiempoReal
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener los datos: {str(e)}"
        )

def datosResumenCelda(opc_cliente):
    #REVISAR NOMBRE ACTUAL
    try:
        dGeneral = ObtenerNodosOpc(opc_cliente)
        datosReceta = dGeneral.buscarNodoOpcVirtual(indice, nbreObjeto, [
            "Nombre actual", "PesoProducto", "TotalNiveles", "sdda_nivel_actual", "iniciado", "estadoMaquina"
        ])
        datosReceta["estadoMaquina"] = "Activo" if datosReceta.get("estadoMaquina") == 1 else "Inactivo" if datosReceta.get("estadoMaquina") == 2 else "Pausado"

        datosReceta["PesoActualDesmoldado"] = datosReceta.get("PesoProducto") * datosReceta.get("sdda_nivel_actual")
        datosReceta["TiempoTrancurrido"] = obtenerTiempo(datosReceta.get("iniciado"))
        celda = {
            "Desmoldeo": datosReceta,
            "Encajonado": [],
            "Palletizado": []
        }
        return celda
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al obtener los datos: {e}")

def leerDatosReceta(opc_cliente):
    try:
        print("Obteniendo datos del cliente OPC...")
        dGeneral = ObtenerNodosOpc(opc_cliente)
        diccionario = [
            "torre_proxima", 
            "receta_proxima", 
            "ALTO_DE_MOLDE", 
            "ALTO_DE_PRODUCTO",
            "ALTURA_AJUSTE",
            "ALTURA_AJUSTE_N1",
            "ALTURA_DE_BASTIDOR",
            "ALTURA_N1",
            "ANCHO_PRODUCTO",
            "CANTIDAD_NIVELES",
            "DELTA_ENTRE_NIVELES",
            "LARGO_DE_MOLDE", 
            "LARGO_DE_PRODUCTO",
            "MOLDES_POR_NIVEL",
            "NOMBRE",
            "NUMERO_DE_GRIPPER",
            "PESO_DEL_PRODUCTO", 
            "TIPO_DE_MOLDE",
        ]
        
        print("Leyendo receta del OPC...")
        datosReceta = dGeneral.leerRecetaOpc(indice, nbreObjeto2, diccionario)
        
        print(f"Datos de receta obtenidos: {datosReceta}")
        guardarRecetaEnBD(datosReceta)
        
        torre_proxima = datosReceta.get("torre_proxima")
        receta_proxima = datosReceta.get("receta_proxima")
        
        print(f"Valor de torre_proxima obtenido: {torre_proxima}")
        print(f"Valor de receta_proxima obtenido: {receta_proxima}")
        
        db: Session = next(get_db())

        print(f"Consultando en la base de datos para la torre con id: {torre_proxima} y id_recetario: {receta_proxima}")

        torres = db.query(Torre).filter(Torre.id_recetario == receta_proxima).all()
        torresconfiguraciones

        if not torres:
            print("No se encontraron torres para el recetario proporcionado.")
            return {"mensaje": "No se encontraron torres para el recetario proporcionado."}

        try:
            torre_proxima = int(torre_proxima)
            primera_torre = torres[0]
            ntorre_comparacion = int(primera_torre.NTorre) + torre_proxima
            print(f"Valor de ntorre_comparacion: {ntorre_comparacion}")

            for torre in torres:
                try:
                    torre_ntorre = int(torre.NTorre)

                    if torre_ntorre == ntorre_comparacion:
                        print(f"Torre encontrada: ID={torre.id}, NTorre={torre.NTorre}, id_recetario={torre.id_recetario}")
                        
                        datosTorres = {
                            "TAG": torre.id,
                            "id": torre.NTorre,
                            "hBastidor": torre.hBastidor,
                            "hAjuste": torre.hAjuste,
                            "hAjusteN1": torre.hAjusteN1,
                            "DisteNivel": torre.DisteNivel,
                        }
                        
                        print(f"Datos de torre: {datosTorres}")

                        # Llamar a la función para escribir en los nodos OPC
                        if escribirDatosTorreOpc(opc_cliente, datosTorres):
                            print("Datos de la torre escritos correctamente en los nodos OPC.")
                        else:
                            print("Error al escribir datos de la torre en los nodos OPC.")

                        return datosTorres

                except Exception as e:
                    print(f"Se produjo un error al procesar la torre: {e}")
                    continue  

            print("Torre o receta no encontrada.")
            return {"mensaje": "Torre o receta no encontrada"}

        except Exception as e:
            print(f"Se produjo un error: {e}")
            return {"mensaje": f"Error: {e}"}

    except Exception as e:
        print(f"Se produjo un error en la función leerDatosReceta: {e}")
        return {"mensaje": f"Error en la función leerDatosReceta: {e}"}

def escribirDatosTorreOpc(opc_cliente, datos_torre):
    try:
        root_node = opc_cliente.get_objects_nodos()
        objects_node = root_node.get_child(["0:Objects"])
        server_interface_node = objects_node.get_child(["2:ServerInterfaces"])
        server_interface_2 = server_interface_node.get_child(["2:Server interface_2"])

        if not server_interface_2:
            logger.error("No se encontró 'Server interface_2'.")
            return False

        # Acceder a "2:DatosTorre"
        datos_torre_node = server_interface_2.get_child(["2:DatosTorre"])
        if not datos_torre_node:
            logger.error("No se encontró el nodo 'DatosTorre'.")
            return False
        
        # Mapeo de la base de datos a los nodos OPC
        mapping = {
            "DisteNivel": "Coreccion_DisteNivel",
            "hAjuste": "Coreccion_hAjuste",
            "hAjusteN1": "Coreccion_hAjusteN1",
            "hBastidor": "Coreccion_hBastidor",
            "TAG": "TAG",
        }

        # Escribir valores en los nodos OPC
        for db_field, opc_node in mapping.items():
            try:
                valor = datos_torre.get(db_field, None)
                if valor is not None:
                    nodo = datos_torre_node.get_child([f"2:{opc_node}"])
                    if nodo is not None:
                        nodo.set_value(valor)
                        logger.info(f"Escrito {db_field} -> {opc_node}: {valor}")
                    else:
                        logger.error(f"No se encontró el nodo OPC para {opc_node}.")
                else:
                    logger.warning(f"El campo {db_field} no tiene valor para escribir.")
            except Exception as e:
                logger.error(f"Error escribiendo {opc_node}: {e}")

        return True

    except Exception as e:
        logger.error(f"Error en la escritura de datos en OPC: {e}")
        return False

def guardarRecetaEnBD(datosReceta):
    try:
        db: Session = next(get_db())
        receta_id = datosReceta.get("receta_proxima")

        if receta_id is None:
            print("Error: receta_proxima es None, no se puede actualizar la receta.")
            return

        receta_existente = db.query(Recetario).filter(Recetario.id == receta_id).first()

        if receta_existente:
            receta_existente.altoMolde = datosReceta.get("alto_de_molde")
            receta_existente.altoProducto = datosReceta.get("alto_de_producto")
            receta_existente.ajusteAltura = datosReceta.get("altura_ajuste")
            receta_existente.ajusteN1Altura = datosReceta.get("altura_ajuste_n1")
            receta_existente.bastidorAltura = datosReceta.get("altura_de_bastidor")
            receta_existente.n1Altura = datosReceta.get("altura_n1")
            receta_existente.anchoProducto = datosReceta.get("ancho_producto")
            receta_existente.cantidadNiveles = datosReceta.get("cantidad_niveles")
            receta_existente.deltaNiveles = datosReceta.get("delta_entre_niveles")
            receta_existente.largoMolde = datosReceta.get("largo_de_molde")
            receta_existente.largoProducto = datosReceta.get("largo_de_producto")
            receta_existente.moldesNivel = datosReceta.get("moldes_por_nivel")
            receta_existente.codigoProducto = datosReceta.get("nombre")
            receta_existente.nroGripper = datosReceta.get("numero_de_gripper")
            receta_existente.pesoProducto = datosReceta.get("peso_del_producto")
            receta_existente.tipoMolde = datosReceta.get("tipo_de_molde")
            print(f"Receta {receta_id} actualizada correctamente.")
        else:
            nueva_receta = Recetario(
                id=receta_id,
                altoMolde=datosReceta.get("alto_de_molde"),
                altoProducto=datosReceta.get("alto_de_producto"),
                ajusteAltura=datosReceta.get("altura_ajuste"),
                ajusteN1Altura=datosReceta.get("altura_ajuste_n1"),
                bastidorAltura=datosReceta.get("altura_de_bastidor"),
                n1Altura=datosReceta.get("altura_n1"),
                anchoProducto=datosReceta.get("ancho_producto"),
                cantidadNiveles=datosReceta.get("cantidad_niveles"),
                deltaNiveles=datosReceta.get("delta_entre_niveles"),
                largoMolde=datosReceta.get("largo_de_molde"),
                largoProducto=datosReceta.get("largo_de_producto"),
                moldesNivel=datosReceta.get("moldes_por_nivel"),
                codigoProducto=datosReceta.get("nombre"),
                nroGripper=datosReceta.get("numero_de_gripper"),
                pesoProducto=datosReceta.get("peso_del_producto"),
                tipoMolde=datosReceta.get("tipo_de_molde"),
            )
            db.add(nueva_receta)
            print(f"Receta {receta_id} creada correctamente.")

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Error al guardar o actualizar la receta en la base de datos: {e}")

    finally:
        db.close()