from opcua import Server
from datetime import datetime
import time
import random
import socket

localIp = socket.gethostbyname(socket.gethostname())

# Crear una instancia del servidor
server = Server()

# Configurar el servidor
server.set_endpoint(f"opc.tcp://{localIp}:4840")  # Dirección y puerto del servidor
server.set_server_name("Servidor OPC UA de Ejemplo")

# Espacio de nombres para los nodos
uri = "http://example.org/opcua/server/"
idx = server.register_namespace(uri)

# Crear un objeto en el servidor
receta_obj = server.nodes.objects.add_object(idx, "RecetaActual")

# Agregar una variable al objeto
var = receta_obj.add_variable(idx, "MiVariable", 0)  # Nombre y valor inicial de la variable
nombre_receta = receta_obj.add_variable(idx, "NombreReceta", "algo01")
proxima_receta = receta_obj.add_variable(idx, "ProximaReceta", "BeforeAlgo01")
nro_gripper = receta_obj.add_variable(idx, "NroGripper", 1)
peso_total_producto = receta_obj.add_variable(idx, "PesoTotalProducto", 10.0)
peso_nivel_torre_prod = receta_obj.add_variable(idx, "PesoNivelTorreProd", 2.0)
torre_nivel_actual = receta_obj.add_variable(idx, "TorreNivelActual", 3)
estado = receta_obj.add_variable(idx, "Estado", "Banda A")

datosGripper = server.nodes.objects.add_object(idx, "datosGripper")
codGripperActual = datosGripper.add_variable(idx, "codGripperActual", 2)
codGripperProx = datosGripper.add_variable(idx, "codGripperProximo", 3)
grippersDisponibles = datosGripper.add_variable(idx, "grippersDisponibles", 5)

datosRobot = server.nodes.objects.add_object(idx, "datosRobot")
posicionX = datosRobot.add_variable(idx, "posicionX", 20)
posicionY = datosRobot.add_variable(idx, "posicionY", 40)
posicionZ = datosRobot.add_variable(idx, "posicionZ", 0)

datosTorre = server.nodes.objects.add_object(idx, "datosTorre")
torreActual = datosTorre.add_variable(idx, "torreActual", 20)
torrePoxima = datosTorre.add_variable(idx, "torrePoxima", 40)
desmoldeoBanda = datosTorre.add_variable(idx, "desmoldeoBanda", 0)

datosSdda = server.nodes.objects.add_object(idx, "datosSdda")
sdda_long_mm = datosSdda.add_variable(idx, "sdda_long_mm", 32)
sdda_vertical_mm = datosSdda.add_variable(idx, "sdda_vertical_mm", 60)
sdda_nivel_actual = datosSdda.add_variable(idx, "sdda_nivel_actual", 8)

sector_IO = server.nodes.objects.add_object(idx, "sector_IO")
boolean01 = sector_IO.add_variable(idx, "boolean01", True)
boolean02 = sector_IO.add_variable(idx, "boolean02", False)
IO_YY_EQ_XX = sector_IO.add_variable(idx, "IO_YY_EQ_XX", True)
estadoMaquina = sector_IO.add_variable(idx, "estadoMaquina", False)


# Iniciar el servidor
server.start()

print("Servidor OPC UA iniciado en: opc.tcp://192.168.1.4:4840")
try:
    while True:
        # Actualizar el valor de la variable
        nuevo_valor = datetime.now().second  # Ejemplo: usar el segundo actual
        var.set_value(nuevo_valor)
        print(f"Valor actualizado: {nuevo_valor}")

        # Actualizar los valores de las variables de la receta
        nombre_receta.set_value(f"algo{random.randint(1, 100):02}")
        proxima_receta.set_value(f"BeforeAlgo{random.randint(1, 100):02}")
        nro_gripper.set_value(random.randint(1, 10))
        peso_total_producto.set_value(round(random.uniform(5.0, 20.0), 2))
        peso_nivel_torre_prod.set_value(round(random.uniform(1.0, 5.0), 2))
        torre_nivel_actual.set_value(random.randint(1, 5))
        estado.set_value(random.choice(["Banda A", "Banda B", "Banda C", "Banda D"]))

        time.sleep(1)
except KeyboardInterrupt:
    print("Servidor detenido.")
finally:
    server.stop()
    print("Servidor apagado.")
