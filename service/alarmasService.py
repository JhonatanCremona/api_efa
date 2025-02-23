from service.opcService import ObtenerNodosOpc
from fastapi import HTTPException
from sqlalchemy.orm import Session

import websockets
import datetime
import logging
import gc

from models.historicoAlarma import HistoricoAlarma
from config import db
logger = logging.getLogger("uvicorn")

listaAlarmas = [
    # Notificaciones (15 elementos)
    {
        "id_alarma": 1,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación",
        "descripcion": "Finalizó ciclo de desmoldeo",
        "fechaActual": "2025/01/14 08:15:30"
    },
    {
        "id_alarma": 2,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación",
        "descripcion": "Torre lista para iniciar encajonado",
        "fechaActual": "2025/01/14 08:17:45"
    },
    {
        "id_alarma": 3,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación ",
        "descripcion": "Producto desmoldado con éxito",
        "fechaActual": "2025/01/14 08:20:00"
    },
    {
        "id_alarma": 4,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación ",
        "descripcion": "Proceso de encajonado iniciado",
        "fechaActual": "2025/01/14 08:25:30"
    },
    {
        "id_alarma": 5,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación ",
        "descripcion": "Ciclo de limpieza completado",
        "fechaActual": "2025/01/14 08:30:00"
    },
    {
        "id_alarma": 6,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación ",
        "descripcion": "Nueva torre cargada en la máquina",
        "fechaActual": "2025/01/14 08:35:15"
    },
    {
        "id_alarma": 7,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación ",
        "descripcion": "Gripper calibrado correctamente",
        "fechaActual": "2025/01/14 08:40:25"
    },
    {
        "id_alarma": 8,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación ",
        "descripcion": "Proceso pausado por falta de insumos",
        "fechaActual": "2025/01/14 08:45:40"
    },
    {
        "id_alarma": 9,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación ",
        "descripcion": "Torre desmontada correctamente",
        "fechaActual": "2025/01/14 08:50:10"
    },
    {
        "id_alarma": 10,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación ",
        "descripcion": "Preparando para reiniciar ciclo",
        "fechaActual": "2025/01/14 08:55:20"
    },
    {
        "id_alarma": 11,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación ",
        "descripcion": "Inspección manual requerida",
        "fechaActual": "2025/01/14 08:58:00"
    },
    {
        "id_alarma": 12,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación ",
        "descripcion": "Fin del turno del operador",
        "fechaActual": "2025/01/14 09:00:30"
    },
    {
        "id_alarma": 13,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación ",
        "descripcion": "Control de calidad completado",
        "fechaActual": "2025/01/14 09:05:00"
    },
    {
        "id_alarma": 14,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación ",
        "descripcion": "Gripper sin actividad",
        "fechaActual": "2025/01/14 09:10:30"
    },
    {
        "id_alarma": 15,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación ",
        "descripcion": "Esperando nueva torre para iniciar ciclo",
        "fechaActual": "2025/01/14 09:15:00"
    },

    # Alertas (20 elementos)
    {
        "id_alarma": 16,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta ",
        "descripcion": "Robot detectó anomalía en el gripper",
        "fechaActual": "2025/01/14 09:20:10"
    },
    {
        "id_alarma": 17,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta",
        "descripcion": "Gripper requiere mantenimiento preventivo",
        "fechaActual": "2025/01/14 09:25:30"
    },
    {
        "id_alarma": 18,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta",
        "descripcion": "Producto atorado en el molde",
        "fechaActual": "2025/01/14 09:30:15"
    },
    {
        "id_alarma": 19,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta",
        "descripcion": "Temperatura del sistema fuera de rango",
        "fechaActual": "2025/01/14 09:35:40"
    },
    {
        "id_alarma": 20,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta",
        "descripcion": "Fuga de aire detectada en la válvula",
        "fechaActual": "2025/01/14 09:40:05"
    },
    {
        "id_alarma": 21,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta",
        "descripcion": "Mal funcionamiento del sensor de presión",
        "fechaActual": "2025/01/14 09:45:30"
    },
    {
        "id_alarma": 22,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta",
        "descripcion": "Sistema de sujeción con baja presión",
        "fechaActual": "2025/01/14 09:50:45"
    },
    {
        "id_alarma": 23,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta",
        "descripcion": "Error de comunicación entre robots",
        "fechaActual": "2025/01/14 09:55:10"
    },
    {
        "id_alarma": 24,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta",
        "descripcion": "Fallo en el sistema de visión",
        "fechaActual": "2025/01/14 10:00:25"
    },
    {
        "id_alarma": 25,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta",
        "descripcion": "Falta de material en línea de producción",
        "fechaActual": "2025/01/14 10:05:40"
    },
    {
        "id_alarma": 26,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta",
        "descripcion": "Luz de advertencia activada en el panel",
        "fechaActual": "2025/01/14 10:10:00"
    },
    {
        "id_alarma": 27,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta",
        "descripcion": "Fallo en el motor de la máquina",
        "fechaActual": "2025/01/14 10:15:25"
    },
    {
        "id_alarma": 28,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta",
        "descripcion": "Movimiento no autorizado detectado en la zona de trabajo",
        "fechaActual": "2025/01/14 10:20:30"
    },
    {
        "id_alarma": 29,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta",
        "descripcion": "Error en el sistema de transporte de materiales",
        "fechaActual": "2025/01/14 10:25:50"
    },
    {
        "id_alarma": 30,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta",
        "descripcion": "Desviación en el ciclo de producción detectada",
        "fechaActual": "2025/01/14 10:30:15"
    },
    {
        "id_alarma": 31,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta",
        "descripcion": "Baja en la eficiencia del robot de paletizado",
        "fechaActual": "2025/01/14 10:35:35"
    },
    {
        "id_alarma": 32,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta",
        "descripcion": "Cierre de seguridad no operable",
        "fechaActual": "2025/01/14 10:40:00"
    },
    {
        "id_alarma": 33,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta",
        "descripcion": "Peligro por sobrecarga de energía",
        "fechaActual": "2025/01/14 10:45:20"
    },
    {
        "id_alarma": 34,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta",
        "descripcion": "Tensión incorrecta en el sistema eléctrico",
        "fechaActual": "2025/01/14 10:50:45"
    },
    {
        "id_alarma": 35,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta",
        "descripcion": "Baja velocidad en la línea de producción",
        "fechaActual": "2025/01/14 10:55:10"
    },

    # Errores (25 elementos)
    {
        "id_alarma": 36,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error",
        "descripcion": "Error de calibración del sistema de visión",
        "fechaActual": "2025/01/14 11:00:15"
    },
    {
        "id_alarma": 37,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error",
        "descripcion": "Fallo en el motor de desplazamiento del robot",
        "fechaActual": "2025/01/14 11:05:40"
    },
    {
        "id_alarma": 38,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error",
        "descripcion": "Temperatura interna del robot excesiva",
        "fechaActual": "2025/01/14 11:10:05"
    },
    {
        "id_alarma": 39,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error",
        "descripcion": "Error en la válvula de aire comprimido",
        "fechaActual": "2025/01/14 11:15:30"
    },
    {
        "id_alarma": 40,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error",
        "descripcion": "Fallo de comunicación con el PLC",
        "fechaActual": "2025/01/14 11:20:50"
    },
    {
        "id_alarma": 41,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error",
        "descripcion": "Desajuste en el sistema de paletizado",
        "fechaActual": "2025/01/14 11:25:00"
    },
    {
        "id_alarma": 42,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error",
        "descripcion": "Falta de material en el transportador",
        "fechaActual": "2025/01/14 11:30:20"
    },
    {
        "id_alarma": 43,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error",
        "descripcion": "Falla en el motor de la línea de producción",
        "fechaActual": "2025/01/14 11:35:40"
    },
    {
        "id_alarma": 44,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error",
        "descripcion": "Baja presión de aire en la línea de producción",
        "fechaActual": "2025/01/14 11:40:00"
    },
    {
        "id_alarma": 45,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error",
        "descripcion": "Error en la calibración de la máquina de encajonado",
        "fechaActual": "2025/01/14 11:45:20"
    },
    {
        "id_alarma": 46,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error",
        "descripcion": "Falta de energía en la unidad de sujeción",
        "fechaActual": "2025/01/14 11:50:40"
    },
    {
        "id_alarma": 47,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error",
        "descripcion": "Sensor de proximidad defectuoso",
        "fechaActual": "2025/01/14 11:55:50"
    },
    {
        "id_alarma": 48,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error",
        "descripcion": "Sistema de detección de peso fallando",
        "fechaActual": "2025/01/14 12:00:00"
    },
    {
        "id_alarma": 49,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error",
        "descripcion": "Máquina de paletizado fuera de servicio",
        "fechaActual": "2025/01/14 12:05:25"
    },
    {
        "id_alarma": 50,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error",
        "descripcion": "Fallo en el sensor de temperatura de la torre",
        "fechaActual": "2025/01/14 12:10:10"
    },
]

listaLogsAlarmas = []
db_session: Session = db.get_db().__next__()

historico_alarmas = {}

def enviarDatosAlarmas(opc_cliente):
    try:
        dbDatosAlarmas = ObtenerNodosOpc(opc_cliente)
        todasAlarmas = dbDatosAlarmas.leerNodoAlarma(5, "Server interface_2", "Alarma")

        for alarma in listaAlarmas:
            fecha_actual = datetime.datetime.now()
            if todasAlarmas[alarma["id_alarma"] -1 ] :
                alarma["estadoAlarma"] = "Activo"
                alarma["fechaActual"] = fecha_actual.strftime("%Y-%m-%d-%H-%M")
                alarma["fechaInicio"] = fecha_actual.strftime("%Y-%m-%d-%H-%M")
                if alarma["id_alarma"] not in historico_alarmas:
                    historico_alarmas[alarma["id_alarma"]] = alarma["id_alarma"]
                    print(f"ALARMA NUEVA AGREGADA: {alarma["id_alarma"]}estado: {alarma["estadoAlarma"]} --- LISTA: {historico_alarmas}")
                    try:
                        historicoAlarma = HistoricoAlarma(
                            id_alarma = 1,
                            id_ciclo = 1
                        )
                        db_session.add(historicoAlarma)
                        logger.info("************GUARDE DATOS EN LA BDD ALARMAS********************")
                        db_session.commit()
                    except Exception as e:
                        db_session.rollback()
                        print("Error", e)
                        raise HTTPException(status=500, detail=f"Error al agregar historico de alarma: {e}")

                listaLogsAlarmas.append(alarma)
            else:
                print(f"ELimine registros {alarma["id_alarma"]} estado: {alarma["estadoAlarma"]} - lista acta{historico_alarmas}")
                if historico_alarmas.get("id") == alarma["id_alarma"]:
                    del historico_alarmas["id"]
                alarma.pop("fechaInicio", None)
                alarma["estadoAlarma"] = "Inactivo"
                alarma["fechaActual"] = fecha_actual.strftime("%Y-%m-%d-%H-%M")
        
        listaAlarmas.sort(key=lambda x: (
            x["estadoAlarma"] != "Activo",  # Ordena primero los "Activo"
            datetime.strptime(x["fechaActual"], "%Y/%m/%d %H:%M:%S")  # Luego ordena por fecha
        ))  
        
        return listaAlarmas, listaLogsAlarmas
    
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al obtener la lista de nodos: {e}")

#Metodo de eliminar elementos de un diccionario que tenga 1hora antiguedad 
#Metodo de Enviar datos LOgs de alarmas

def eliminarRegistroLogsAlarma(listaAlarmas):
    now = datetime.datetime.now()
    fecha_1hora_atras = now - datetime.timedelta(hours=1)
    estadoEliminarAlarma = False

    # Iterar en orden inverso
    for i in range(len(listaAlarmas) - 1, -1, -1):
        alarma = listaAlarmas[i]
        fecha_alarma = datetime.datetime.strptime(alarma["fechaActual"], "%Y-%m-%d-%H-%M")
        if fecha_alarma < fecha_1hora_atras:
            del listaAlarmas[i]  # Elimina el elemento en el índice
            estadoEliminarAlarma = True

    return estadoEliminarAlarma

def enviaListaLogsAlarmas():

    if eliminarRegistroLogsAlarma(listaLogsAlarmas):
        logger.info(f"SE ELIMINARON DATOS DE LA LISTA DE LOGS ALARMAS: {listaLogsAlarmas}")
    else:
        logger.warning(f"NO SE ELIMINARON DATOS DE LA LISTA DE LOGS ALARMAS")

    return listaLogsAlarmas

