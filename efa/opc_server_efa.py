import time
import random
from opcua import Server
import socket
import threading
from threading import Thread
import asyncio
from opcua import ua

# Obtener la IP local para configurar el endpoint
local_ip = socket.gethostbyname(socket.gethostname())

# Crear una instancia del servidor OPC UA
server = Server()

# Configurar el servidor
server.set_endpoint(f"opc.tcp://{local_ip}:4840")
server.set_server_name("Servidor OPC UA - Datos Dinámicos")

# Registrar un espacio de nombres para las variables
uri = "http://example.org/opcua/server/"
idx = server.register_namespace(uri)

objects = server.nodes.objects
server_interfaces = objects.add_object(idx, "ServerInterfaces")
receta_obj = server_interfaces.add_object(idx, "Server interface_1")
datos_enviar = receta_obj.add_object(idx, "DATOS OPC A ENVIAR")

lista_alarmas = datos_enviar.add_object(idx, "Alarmas")

grupo_alarmas = [
    "CANCELACION",
    "FALLAS CILINDROS",
    "GENERALES",
    "INICIO DE CICLO",
    "POSICIONADOR",
    "PULSADORES",
    "ROBOT",
    "SDDA",
    "SERVOS"
]

# Crear subnodos y sus arrays
for grupo in grupo_alarmas:
    nodo_grupo = lista_alarmas.add_variable(idx, grupo, 0)
    
    # Crear 20 variables (tipo bool) dentro de cada grupo
    for i in range(20):
        var = nodo_grupo.add_variable(idx, f"[{i}]", False)
        var.set_writable() 

Comprobacion_datos = datos_enviar.add_variable(idx, "Confirmacion_envio", True)

variables = []
estado_equipo = datos_enviar.add_variable(idx, "Estado_equipo", True)
variables+= [
    estado_equipo.add_variable(idx, "Ciclo_iniciado", False),
    estado_equipo.add_variable(idx, "Estado_actual", 2),
    estado_equipo.add_variable(idx, "Nivel_finalizado", 0)
]

variables += [
    Comprobacion_datos.add_variable(idx, "confirmacion_envio",True),
    Comprobacion_datos.add_variable(idx, "receta_obtenido", 1),
    Comprobacion_datos.add_variable(idx, "torre_obtenido", 1) 
]

nivelesHN = datos_enviar.add_variable(idx, "DatosNivelesHN", 0)  # Se crea solo una vez
variables += [
    nivelesHN.add_variable(idx, "Correccion_hN1", "1"),
    nivelesHN.add_variable(idx, "Correccion_hN2", "2"),
    nivelesHN.add_variable(idx, "Correccion_hN3", "3"),
    nivelesHN.add_variable(idx, "Correccion_hN4", "4"),
    nivelesHN.add_variable(idx, "Correccion_hN5", "5"),
    nivelesHN.add_variable(idx, "Correccion_hN6", "6"),
    nivelesHN.add_variable(idx, "Correccion_hN7", "7"),
    nivelesHN.add_variable(idx, "Correccion_hN8", "8"),
    nivelesHN.add_variable(idx, "Correccion_hN9", "9"),
    nivelesHN.add_variable(idx, "Correccion_hN10", "10"),
    nivelesHN.add_variable(idx, "Correccion_hN11", "11"),
]

nivelesuHN = datos_enviar.add_variable(idx, "DatosNivelesuHN", 0)  # Se crea solo una vez
variables += [
    nivelesuHN.add_variable(idx, "ultimo_hNivel1", "1"),
    nivelesuHN.add_variable(idx, "ultimo_hNivel2", "2"),
    nivelesuHN.add_variable(idx, "ultimo_hNivel3", "3"),
    nivelesuHN.add_variable(idx, "ultimo_hNivel4", "4"),
    nivelesuHN.add_variable(idx, "ultimo_hNivel5", "5"),
    nivelesuHN.add_variable(idx, "ultimo_hNivel6", "6"),
    nivelesuHN.add_variable(idx, "ultimo_hNivel7", "7"),
    nivelesuHN.add_variable(idx, "ultimo_hNivel8", "8"),
    nivelesuHN.add_variable(idx, "ultimo_hNivel9", "9"),
    nivelesuHN.add_variable(idx, "ultimo_hNivel10", "10"),
    nivelesuHN.add_variable(idx, "ultimo_hNivel11", "11"),
]

nivelesChG = datos_enviar.add_variable(idx, "DatosNivelesChG",0)  # Se crea solo una vez
variables += [
    nivelesChG.add_variable(idx, "Correccion_hguardado_N1", "1"),
    nivelesChG.add_variable(idx, "Correccion_hguardado_N2", "2"),
    nivelesChG.add_variable(idx, "Correccion_hguardado_N3", "3"),
    nivelesChG.add_variable(idx, "Correccion_hguardado_N4", "4"),
    nivelesChG.add_variable(idx, "Correccion_hguardado_N5", "5"),
    nivelesChG.add_variable(idx, "Correccion_hguardado_N6", "6"),
    nivelesChG.add_variable(idx, "Correccion_hguardado_N7", "7"),
    nivelesChG.add_variable(idx, "Correccion_hguardado_N8", "8"),
    nivelesChG.add_variable(idx, "Correccion_hguardado_N9", "9"),
    nivelesChG.add_variable(idx, "Correccion_hguardado_N10", "10"),
    nivelesChG.add_variable(idx, "Correccion_hguardado_N11", "11"),
]

nivelesChB = datos_enviar.add_variable(idx, "DatosNivelesChB",0)  # Se crea solo una vez
variables += [
    nivelesChB.add_variable(idx, "Correccion_hbusqueda_N1", "1"),
    nivelesChB.add_variable(idx, "Correccion_hbusqueda_N2", "2"),
    nivelesChB.add_variable(idx, "Correccion_hbusqueda_N3", "3"),
    nivelesChB.add_variable(idx, "Correccion_hbusqueda_N4", "4"),
    nivelesChB.add_variable(idx, "Correccion_hbusqueda_N5", "5"),
    nivelesChB.add_variable(idx, "Correccion_hbusqueda_N6", "6"),
    nivelesChB.add_variable(idx, "Correccion_hbusqueda_N7", "7"),
    nivelesChB.add_variable(idx, "Correccion_hbusqueda_N8", "8"),
    nivelesChB.add_variable(idx, "Correccion_hbusqueda_N9", "9"),
    nivelesChB.add_variable(idx, "Correccion_hbusqueda_N10", "10"),
    nivelesChB.add_variable(idx, "Correccion_hbusqueda_N11", "11"),
]

nivelesFA = datos_enviar.add_variable(idx, "DatosNivelesFA",0)  # Se crea solo una vez
variables += [
    nivelesFA.add_variable(idx, "FallasN1", "1"),
    nivelesFA.add_variable(idx, "FallasN2", "2"),
    nivelesFA.add_variable(idx, "FallasN3", "3"),
    nivelesFA.add_variable(idx, "FallasN4", "4"),
    nivelesFA.add_variable(idx, "FallasN5", "5"),
    nivelesFA.add_variable(idx, "FallasN6", "6"),
    nivelesFA.add_variable(idx, "FallasN7", "7"),
    nivelesFA.add_variable(idx, "FallasN8", "8"),
    nivelesFA.add_variable(idx, "FallasN9", "9"),
    nivelesFA.add_variable(idx, "FallasN10", "10"),
    nivelesFA.add_variable(idx, "FallasN11", "11"),
]

datos_gripper = datos_enviar.add_variable(idx, "datosGripper", True)
variables += [
    datos_gripper.add_variable(idx, "NGripperActual", 2),
    datos_gripper.add_variable(idx, "NGripperProximo", 3),
]

datos_robot = datos_enviar.add_variable(idx, "datosRobot", True)
variables += [
    datos_robot.add_variable(idx, "posicionX", 20),
    datos_robot.add_variable(idx, "posicionY", 40),
    datos_robot.add_variable(idx, "posicionZ", 0),
]

datos_sdda = datos_enviar.add_variable(idx, "datosSdda", True)
variables += [
    datos_sdda.add_variable(idx, "sdda_long_mm", 0),
    datos_sdda.add_variable(idx, "sdda_nivel_actual", 1),
    datos_sdda.add_variable(idx, "sdda_vertical_mm", 0)
]

datos_seleccionados = datos_enviar.add_variable(idx, "datosSeleccionados", True)
variables += [
    datos_seleccionados.add_variable(idx, "N_receta_actual", 0),
    datos_seleccionados.add_variable(idx, "N_receta_proxima", 0),
    datos_seleccionados.add_variable(idx, "N_torre_actual", 0),
    datos_seleccionados.add_variable(idx, "N_torre_proxima", 0),
    datos_seleccionados.add_variable(idx, "pantalla_receta", True),
] 

datos_torre = datos_enviar.add_variable(idx, "datosTorre", True)
variables += [
    datos_torre.add_variable(idx, "TAG", "Cuadrado"),
    datos_torre.add_variable(idx, "Correccion_hBastidor", 1),
    datos_torre.add_variable(idx, "Correccion_hAjuste", 2),
    datos_torre.add_variable(idx, "Correccion_hAjusteN1", 3),
    datos_torre.add_variable(idx, "Correccion_DisteNivel", 4),
]

desmoldeo = datos_enviar.add_variable(idx, "desmoldeo", True)
variables+= [
    desmoldeo.add_variable(idx, "cicloTiempoTotal", 1),
    desmoldeo.add_variable(idx, "cicloTipoFin", 1),
    desmoldeo.add_variable(idx, "desmoldeobanda",1)
]

recetario = datos_enviar.add_variable(idx, "RECETARIO", 0)

# Lista de variables por receta
variables_receta = [
    "ALTO DE MOLDE",
    "ALTO DE PRODUCTO",
    "ALTURA AJUSTE",
    "ALTURA AJUSTE N1",
    "ALTURA DE BASTIDOR",
    "ALTURA N1",
    "ANCHO PRODUCTO",
    "CANTIDAD NIVELES",
    "DELTA ENTRE NIVELES",
    "LARGO DE MOLDE",
    "LARGO DE PRODUCTO",
    "MOLDES POR NIVEL",
    "NOMBRE",
    "NUMERO DE GRIPPER",
    "PESO DEL PRODUCTO",
    "PRODUCTOS POR MOLDE",
    "TIPO DE MOLDE"
]
RecetaNombres = [
    "(OV-A) OVALADO A",
    "(OV-B) OVALADO B",
    "(CU) CUADRADO",
    "(QP) QUESO PUERCO",
    "(7K) RECTANGULAR",
    "(6K) MANDOLINA",
    "(LU) LUNCH"
]


# Crear 20 recetas con las variables
for i in range(20):
    receta = recetario.add_variable(idx, f"[{i}]", 0)
    for var_name in variables_receta:
        if var_name == "NOMBRE":
            nombre_valor = RecetaNombres[i] if i < len(RecetaNombres) else ""
            receta.add_variable(idx, var_name, nombre_valor)
        elif var_name == "CANTIDAD NIVELES":
            receta.add_variable(idx, var_name, 11)
        elif var_name == "PRODUCTOS POR MOLDE":
            receta.add_variable(idx, var_name, 6)
        elif var_name == "PESO DEL PRODUCTO":
            receta.add_variable(idx, var_name, 14.9)
        else:
            receta.add_variable(idx, var_name, 1)


ALTURA_TORRE_MM = 2000
NIVELES_TORRE = 11
ALTURA_SEGURIDAD_MM = 2000

# Alturas por nivel (en mm)
ALTURAS_Z = [int(i * ALTURA_TORRE_MM / NIVELES_TORRE) for i in range(NIVELES_TORRE)]

# Valores posibles de Y (en mm)
VALORES_Y = list(range(-500, 510, 100))

def simular_movimiento_robot(x, y, z):
    """
    Simula el movimiento del brazo KUKA en coordenadas cartesianas.
    """
    print(f"🔧 Movimiento del brazo: X={x} mm, Y={y} mm, Z={z} mm")

def mover_robot_a_altura_segura():
    """
    Simula la subida del brazo a la altura de seguridad.
    """
    simular_movimiento_robot(1000, 0, ALTURA_SEGURIDAD_MM)
    print("🔼 El brazo se posicionó en altura segura.\n")

def ciclo_de_desmoldeo():
    global variables

    idReceta_actual = 1
    RecetaNombres = [
    "(OV-A) OVALADO A",
    "(OV-B) OVALADO B",
    "(CU) CUADRADO",
    "(QP) QUESO PUERCO",
    "(7K) RECTANGULAR",
    "(6K) MANDOLINA",
    "(LU) LUNCH"
    ]
    gripper_actual = 1
    torre_actual = 1
    torre_proxima = 2
    estado_maquina = 1
    desmoldeo_banda = 1
    valor_X = 0

    while True:
        receta_nombre = RecetaNombres[idReceta_actual - 1]
        print(f"\n🟢 Iniciando ciclo de desmoldeo para la receta: {receta_nombre}")

        for repeticion in range(1, 2):
            print(f"\n🔁 Repetición {repeticion}/2")
            receta_0 = recetario.get_child([f"2:[{idReceta_actual}]"])

            peso_producto_node = receta_0.get_child(["2:PESO DEL PRODUCTO"])
            
            nuevo_peso = random.uniform(14.3, 16)  # por ejemplo un nuevo peso random
            peso_producto_node.set_value(nuevo_peso)

            for nivel_actual in range(1, 12):
                print(f"Torre {torre_actual}, Nivel {nivel_actual}")
                estado_maquina = 2

                # Obtener altura Z del nivel actual (en mm)
                altura_nivel_z = ALTURAS_Z[nivel_actual - 1]
                posicion_y = random.choice(VALORES_Y)
                valor_X = 0
                # Simular movimiento hacia el molde
                simular_movimiento_robot(valor_X, posicion_y, altura_nivel_z)
                print("🧲 Brazo recoge el molde del nivel")

                # Actualizar variables en el servidor OPC UA
                for var in variables:
                    if var.get_browse_name().Name == "N_receta_actual":
                        var.set_value(idReceta_actual)
                    elif var.get_browse_name().Name == "N_receta_proxima":
                        var.set_value((idReceta_actual % len(RecetaNombres)) + 1)
                        print(f"VALOR DE RECETA PROXIMO------ {var.get_value()}")
                    elif var.get_browse_name().Name == "N_torre_actual":
                        var.set_value(torre_actual)
                    elif var.get_browse_name().Name == "N_torre_proxima":
                        var.set_value(torre_proxima)
                    elif var.get_browse_name().Name == "sdda_nivel_actual":
                        var.set_value(nivel_actual)
                    elif var.get_browse_name().Name == "Estado_actual":
                        var.set_value(estado_maquina)
                    elif var.get_browse_name().Name == "desmoldeobanda":
                        var.set_value(desmoldeo_banda)
                    if var.get_browse_name().Name == "posicionX":
                        var.set_value(valor_X)
                    elif var.get_browse_name().Name == "posicionY":
                        var.set_value(posicion_y)
                    elif var.get_browse_name().Name == "posicionZ":
                        var.set_value(altura_nivel_z)
                    elif var.get_browse_name().Name == "Ciclo_iniciado":
                        var.set_value(True)


                valor_X = 1000
                # Simular movimiento hacia zona de descarga
                simular_movimiento_robot(valor_X, posicion_y, altura_nivel_z)
                print("📤 Brazo deposita el molde en la zona de descarga")

                # Subida a altura de seguridad
                mover_robot_a_altura_segura()

                # Simulación de tiempo de procesamiento
                time.sleep(8 * 60 / 11)
                #time.sleep(3)
            idReceta_actual = (idReceta_actual % len(RecetaNombres)) + 1
            print(f"\n Preparando siguiente receta: {idReceta_actual}- {RecetaNombres[idReceta_actual - 1]}")

            dato_ciclo = variables[0]
            dato_ciclo.set_value(False)
            dato_maquina = variables[1]
            dato_maquina.set_value(1)
            time.sleep(5)
            print(f"\n✅ Ciclo de desmoldeo completado para torre {torre_actual}")
            estado_maquina = 1
            gripper_actual = (gripper_actual % 4) + 1
            torre_actual += 1
            torre_proxima = torre_actual + 1
            if torre_actual > 80:
                torre_actual = 1
                torre_proxima = 2

            

        time.sleep(10)

if __name__ == "__main__":
    try:
        print("Servidor OPC UA iniciado en", server.endpoint)
        server.start()
        #thread1.start()
        #thread2.start()
        #thread3.start()
        ciclo_de_desmoldeo()
        
    except KeyboardInterrupt:
        print("\nServidor detenido por el usuario.")
    finally:
        server.stop()
        print("Servidor OPC UA apagado.")
