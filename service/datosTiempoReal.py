from models.receta import Recetas
from fastapi import HTTPException

def resumenEtapaDesmoldeo(opc_cliente):
    try:
        dResumenDatos = Recetas(opc_cliente)
        nbreObjeto = "RecetaActual"
        diccinario = ["NombreReceta", "ProximaReceta","NroGriper", "PesoTotalProducto", "PesoNivelTorreProd", "TorreNivelActual" , "Estado"]
        return dResumenDatos.buscarNodos(2,nbreObjeto, diccinario)
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al obtener la lista de nodos: {e}")

def conversorListaAVectores(lista):
    return list(lista.values())

def obtenerLista(dGeneral, nivel, objeto, diccionario):
    return dGeneral.buscarNodos(nivel, objeto, diccionario)

def datosGenerale(opc_cliente):
    try:
        dGeneral = Recetas(opc_cliente)
        nodos = {
            "datosGenerales": ("RecetaActual", ["NombreReceta", "ProximaReceta", "PesoTotalProducto", "Estado"]),
            "datosGripper": ("datosGripper", ["codGripperActual", "codGripperProximo", "gripperDisponibles"]),
            "datosKuka": ("datosRobot", ["posicionX", "posicionY", "posicionZ"]),
            "datosTorre": ("datosTorre", ["desmoldeoBanda", "torreActual","torreProxima"]),
            "sectorIO": ("sector_IO", ["IO_YY_EQ_XX", "estadoMaquina", "boolean01", "boolean02"]),
            "datosSdda": ("datosSdda", ["sdda_long_mm", "sdda_vertical_mm", "sdda_nivel_actual"])
        }

        listaDatosTiempoReal = {
            clave: conversorListaAVectores(obtenerLista(dGeneral, 2, objeto, diccionario)) for clave, (objeto, diccionario) in nodos.items()
        }
        return listaDatosTiempoReal
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener los datos: {str(e)}"
    )



