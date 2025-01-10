from models.receta import Recetas
from fastapi import HTTPException

def resumenEtapaDesmoldeo(opc_cliente):
    # agregar PesoTotal (actual) - Objeto TORRE: Nivel Actual - Estado (activo / inactivo / pausa) - tiempo transcurrido / Tag Torre ()
    try:
        dResumenDatos = Recetas(opc_cliente)
        nbreObjeto = "RecetaActual"
        diccinario = ["Nombre", "RecetaProximaDesmolde","NroGriper", "PesoProducto", "TotalNiveles" , "TipoMolde"]

        resultado = dResumenDatos.buscarNodos(2,nbreObjeto, diccinario)
        datosTorre = dResumenDatos.buscarNodos(2, "datosTorre", ["NivelActual", "torreActual"])
        resultado = resultado | datosTorre
        resultado["PesoActual"] = resultado.get("PesoProducto") * resultado.get("NivelActual")
        resultado["Estado"] = "Activo" if dResumenDatos.buscarNodo(2,"sector_IO", "estadoMaquina") else "Inactivo"
        resultado["TiempoTranscurrido"] = "00:00 hs"

        return resultado
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al obtener la lista de nodos: {e}")

def conversorListaAVectores(lista):
    return list(lista.values())

def obtenerLista(dGeneral, nivel, objeto, diccionario):
    return dGeneral.buscarNodos(nivel, objeto, diccionario)

def datosGenerale(opc_cliente):
    # agregar PesoTotal y Estado 
    try:
        dGeneral = Recetas(opc_cliente)
        nodos = {
            "datosGenerales": ("RecetaActual", ["Nombre", "RecetaProximaDesmolde", "PesoProducto"]),
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

def datosResumenCelda(opc_cliente):
    lista = []
    try:
        dGeneral = Recetas(opc_cliente)
        datosReceta = dGeneral.buscarNodos(2, "RecetaActual", [
            "Nombre", "PesoProducto", "totalNiveles"
        ])

        pesoActual = datosReceta.get("PesoProducto") * dGeneral.buscarNodo(2, "datosTorre", "NivelActual")

        lista.append(dGeneral.buscarNodo(2, "RecetaActual", "Nombre"))
        lista.append(pesoActual)
        lista.append(dGeneral.buscarNodo(2, "RecetaActual", "PesoProducto"))
        lista.append(dGeneral.buscarNodo(2, "sector_IO", "estadoMaquina"))
        lista.append("00:00hs")

        celda = {
            "Desmoldeo": lista,
            "Encajonado": [],
            "Palletizado": []
        }
        return celda
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al obtener los datos: {e}")
    



