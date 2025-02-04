from service.opcService import ObtenerNodosOpc
from fastapi import HTTPException
from datetime import datetime

from models.ciclo import Ciclo

nbreObjeto = "Server interface_1"
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
        resultado = dResumenDatos.buscarNodos(indice,nbreObjeto, diccinario)
        resultado["estadoMaquina"] = "Activo" if resultado.get("estadoMaquina") == 1 else "Inactivo" if resultado.get("estadoMaquina") == 2 else "Pausado"
        resultado["TiempoTranscurrido"] = obtenerTiempo(resultado.get("iniciado"))
        resultado["PesoActualDesmoldado"] = resultado.get("PesoProducto") * resultado.get("sdda_nivel_actual")
        
        return resultado
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al obtener la lista de nodos: {e}")

def conversorListaAVectores(lista):
    return list(lista.values())

def obtenerLista(dGeneral, nivel, objeto, diccionario):
    return dGeneral.buscarNodos(nivel, objeto, diccionario)

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
        datosReceta = dGeneral.buscarNodos(indice, nbreObjeto, [
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
    



