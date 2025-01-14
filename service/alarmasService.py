from models.receta import Recetas
from fastapi import HTTPException

import websockets
import datetime
import logging
import gc

logger = logging.getLogger("uvicorn")

listaAlarmas = [
    # Notificaciones (15 elementos)
    {
        "id_alarma": 1,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación 01",
        "descripcion": "Finalizó ciclo de desmoldeo",
        "fechaRegistro": "2025/01/14 08:15:30"
    },
    {
        "id_alarma": 2,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación 02",
        "descripcion": "Torre lista para iniciar encajonado",
        "fechaRegistro": "2025/01/14 08:17:45"
    },
    {
        "id_alarma": 3,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación 03",
        "descripcion": "Producto desmoldado con éxito",
        "fechaRegistro": "2025/01/14 08:20:00"
    },
    {
        "id_alarma": 4,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación 04",
        "descripcion": "Proceso de encajonado iniciado",
        "fechaRegistro": "2025/01/14 08:25:30"
    },
    {
        "id_alarma": 5,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación 05",
        "descripcion": "Ciclo de limpieza completado",
        "fechaRegistro": "2025/01/14 08:30:00"
    },
    {
        "id_alarma": 6,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación 06",
        "descripcion": "Nueva torre cargada en la máquina",
        "fechaRegistro": "2025/01/14 08:35:15"
    },
    {
        "id_alarma": 7,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación 07",
        "descripcion": "Gripper calibrado correctamente",
        "fechaRegistro": "2025/01/14 08:40:25"
    },
    {
        "id_alarma": 8,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación 08",
        "descripcion": "Proceso pausado por falta de insumos",
        "fechaRegistro": "2025/01/14 08:45:40"
    },
    {
        "id_alarma": 9,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación 09",
        "descripcion": "Torre desmontada correctamente",
        "fechaRegistro": "2025/01/14 08:50:10"
    },
    {
        "id_alarma": 10,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación 10",
        "descripcion": "Preparando para reiniciar ciclo",
        "fechaRegistro": "2025/01/14 08:55:20"
    },
    {
        "id_alarma": 11,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación 11",
        "descripcion": "Inspección manual requerida",
        "fechaRegistro": "2025/01/14 08:58:00"
    },
    {
        "id_alarma": 12,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación 12",
        "descripcion": "Fin del turno del operador",
        "fechaRegistro": "2025/01/14 09:00:30"
    },
    {
        "id_alarma": 13,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Notificación 13",
        "descripcion": "Control de calidad completado",
        "fechaRegistro": "2025/01/14 09:05:00"
    },
    {
        "id_alarma": 14,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación 14",
        "descripcion": "Gripper sin actividad",
        "fechaRegistro": "2025/01/14 09:10:30"
    },
    {
        "id_alarma": 15,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Notificación 15",
        "descripcion": "Esperando nueva torre para iniciar ciclo",
        "fechaRegistro": "2025/01/14 09:15:00"
    },

    # Alertas (20 elementos)
    {
        "id_alarma": 16,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta 01",
        "descripcion": "Robot detectó anomalía en el gripper",
        "fechaRegistro": "2025/01/14 09:20:10"
    },
    {
        "id_alarma": 17,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta 02",
        "descripcion": "Gripper requiere mantenimiento preventivo",
        "fechaRegistro": "2025/01/14 09:25:30"
    },
    {
        "id_alarma": 18,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta 03",
        "descripcion": "Producto atorado en el molde",
        "fechaRegistro": "2025/01/14 09:30:15"
    },
    {
        "id_alarma": 19,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta 04",
        "descripcion": "Temperatura del sistema fuera de rango",
        "fechaRegistro": "2025/01/14 09:35:40"
    },
    {
        "id_alarma": 20,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta 05",
        "descripcion": "Fuga de aire detectada en la válvula",
        "fechaRegistro": "2025/01/14 09:40:05"
    },
    {
        "id_alarma": 21,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta 06",
        "descripcion": "Mal funcionamiento del sensor de presión",
        "fechaRegistro": "2025/01/14 09:45:30"
    },
    {
        "id_alarma": 22,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta 07",
        "descripcion": "Sistema de sujeción con baja presión",
        "fechaRegistro": "2025/01/14 09:50:45"
    },
    {
        "id_alarma": 23,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta 08",
        "descripcion": "Error de comunicación entre robots",
        "fechaRegistro": "2025/01/14 09:55:10"
    },
    {
        "id_alarma": 24,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta 09",
        "descripcion": "Fallo en el sistema de visión",
        "fechaRegistro": "2025/01/14 10:00:25"
    },
    {
        "id_alarma": 25,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta 10",
        "descripcion": "Falta de material en línea de producción",
        "fechaRegistro": "2025/01/14 10:05:40"
    },
    {
        "id_alarma": 26,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta 11",
        "descripcion": "Luz de advertencia activada en el panel",
        "fechaRegistro": "2025/01/14 10:10:00"
    },
    {
        "id_alarma": 27,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta 12",
        "descripcion": "Fallo en el motor de la máquina",
        "fechaRegistro": "2025/01/14 10:15:25"
    },
    {
        "id_alarma": 28,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta 13",
        "descripcion": "Movimiento no autorizado detectado en la zona de trabajo",
        "fechaRegistro": "2025/01/14 10:20:30"
    },
    {
        "id_alarma": 29,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta 14",
        "descripcion": "Error en el sistema de transporte de materiales",
        "fechaRegistro": "2025/01/14 10:25:50"
    },
    {
        "id_alarma": 30,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta 15",
        "descripcion": "Desviación en el ciclo de producción detectada",
        "fechaRegistro": "2025/01/14 10:30:15"
    },
    {
        "id_alarma": 31,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta 16",
        "descripcion": "Baja en la eficiencia del robot de paletizado",
        "fechaRegistro": "2025/01/14 10:35:35"
    },
    {
        "id_alarma": 32,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta 17",
        "descripcion": "Cierre de seguridad no operable",
        "fechaRegistro": "2025/01/14 10:40:00"
    },
    {
        "id_alarma": 33,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta 18",
        "descripcion": "Peligro por sobrecarga de energía",
        "fechaRegistro": "2025/01/14 10:45:20"
    },
    {
        "id_alarma": 34,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Alerta 19",
        "descripcion": "Tensión incorrecta en el sistema eléctrico",
        "fechaRegistro": "2025/01/14 10:50:45"
    },
    {
        "id_alarma": 35,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Alerta 20",
        "descripcion": "Baja velocidad en la línea de producción",
        "fechaRegistro": "2025/01/14 10:55:10"
    },

    # Errores (25 elementos)
    {
        "id_alarma": 36,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error 01",
        "descripcion": "Error de calibración del sistema de visión",
        "fechaRegistro": "2025/01/14 11:00:15"
    },
    {
        "id_alarma": 37,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error 02",
        "descripcion": "Fallo en el motor de desplazamiento del robot",
        "fechaRegistro": "2025/01/14 11:05:40"
    },
    {
        "id_alarma": 38,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error 03",
        "descripcion": "Temperatura interna del robot excesiva",
        "fechaRegistro": "2025/01/14 11:10:05"
    },
    {
        "id_alarma": 39,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error 04",
        "descripcion": "Error en la válvula de aire comprimido",
        "fechaRegistro": "2025/01/14 11:15:30"
    },
    {
        "id_alarma": 40,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error 05",
        "descripcion": "Fallo de comunicación con el PLC",
        "fechaRegistro": "2025/01/14 11:20:50"
    },
    {
        "id_alarma": 41,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error 06",
        "descripcion": "Desajuste en el sistema de paletizado",
        "fechaRegistro": "2025/01/14 11:25:00"
    },
    {
        "id_alarma": 42,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error 07",
        "descripcion": "Falta de material en el transportador",
        "fechaRegistro": "2025/01/14 11:30:20"
    },
    {
        "id_alarma": 43,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error 08",
        "descripcion": "Falla en el motor de la línea de producción",
        "fechaRegistro": "2025/01/14 11:35:40"
    },
    {
        "id_alarma": 44,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error 09",
        "descripcion": "Baja presión de aire en la línea de producción",
        "fechaRegistro": "2025/01/14 11:40:00"
    },
    {
        "id_alarma": 45,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error 10",
        "descripcion": "Error en la calibración de la máquina de encajonado",
        "fechaRegistro": "2025/01/14 11:45:20"
    },
    {
        "id_alarma": 46,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error 11",
        "descripcion": "Falta de energía en la unidad de sujeción",
        "fechaRegistro": "2025/01/14 11:50:40"
    },
    {
        "id_alarma": 47,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error 12",
        "descripcion": "Sensor de proximidad defectuoso",
        "fechaRegistro": "2025/01/14 11:55:50"
    },
    {
        "id_alarma": 48,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error 13",
        "descripcion": "Sistema de detección de peso fallando",
        "fechaRegistro": "2025/01/14 12:00:00"
    },
    {
        "id_alarma": 49,
        "estadoAlarma": "Inactivo",
        "tipoAlarma": "Error 14",
        "descripcion": "Máquina de paletizado fuera de servicio",
        "fechaRegistro": "2025/01/14 12:05:25"
    },
    {
        "id_alarma": 50,
        "estadoAlarma": "Activo",
        "tipoAlarma": "Error 15",
        "descripcion": "Fallo en el sensor de temperatura de la torre",
        "fechaRegistro": "2025/01/14 12:10:10"
    },
]

listaLogsAlarmas = []
def enviarDatosAlarmas(opc_cliente):

    try:
        dbDatosAlarmas = Recetas(opc_cliente)
        todasAlarmas = dbDatosAlarmas.buscarNodo(2, "alarma", "Array")
        
        for alarma in listaAlarmas:
            fecha_actual = datetime.datetime.now()
            alarma["estadoAlarma"] = "Activo" if todasAlarmas[alarma["id_alarma"] -1 ] else "Inactivo" 
            alarma["fechaRegistro"] = fecha_actual.strftime("%Y-%m-%d-%H-%M")
            listaLogsAlarmas.append(alarma)

        return listaAlarmas
    
    except Exception as e:
        raise HTTPException(status=500, detail=f"Error al obtener la lista de nodos: {e}")

#Metodo de eliminar elementos de un diccionario que tenga 1hora antiguedad 
#Metodo de Enviar datos LOgs de alarmas

def eliminarRegistroLogsAlarma(listaAlarmas):
    now = datetime.datetime.now()
    fecha_1hora_atras = now - datetime.timedelta(minutes=1)
    estadoEliminarAlarma = False

    # Iterar en orden inverso
    for i in range(len(listaAlarmas) - 1, -1, -1):
        alarma = listaAlarmas[i]
        fecha_alarma = datetime.datetime.strptime(alarma["fechaRegistro"], "%Y-%m-%d-%H-%M")
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