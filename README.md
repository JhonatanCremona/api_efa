# Proyecto PLC Data Logger y Reportes

Este proyecto es una aplicación desarrollada con **FastAPI** que lee datos desde un **PLC (Controlador Lógico Programable)**, los almacena en una base de datos y genera reportes sobre los datos adquiridos.

## Descripción

La aplicación se conecta a un PLC para leer datos en tiempo real. Los datos adquiridos se almacenan en una base de datos y se pueden consultar o generar reportes. Está diseñada para facilitar la supervisión y análisis de datos en un entorno de automatización industrial.

### Características principales:

- **Lectura de datos de PLC**: La app se conecta al PLC mediante el protocolo OPC-UA para leer información en tiempo real.
- **Almacenamiento de datos**: Los datos obtenidos se almacenan en una base de datos relacional (MySQL, PostgreSQL, etc.).
- **Generación de reportes**: La app permite generar reportes a partir de los datos almacenados, facilitando el análisis y la toma de decisiones.
- **API RESTful**: Utiliza **FastAPI** para crear una API RESTful rápida y eficiente para interactuar con los datos del PLC.

## Requisitos

A continuación se detallan los requisitos necesarios para ejecutar el proyecto:

- Python 3.8 o superior
- Base de datos como **MySQL** o **PostgreSQL** (configurable)
- PLC compatible con el protocolo **OPC-UA**
- Librerías de Python:
  - **fastapi**: Framework para crear la API REST.
  - **uvicorn**: Servidor ASGI para ejecutar la app FastAPI.
  - **opcua**: Librería para conectarse y leer datos desde el PLC.
  - **sqlalchemy**: ORM para interactuar con la base de datos.

## Instalación

Sigue los siguientes pasos para instalar y ejecutar el proyecto:


2. **Crear y activar un entorno virtual**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate   # En Linux/MacOS
    .\venv\Scripts\activate    # En Windows
    ```

3. **Instalar las dependencias**:
    ```bash
    pip install "fastapi[standard]"
    pip install PyMySQL
    pip install sqlalchemy
    pip install cryptography
    pip install opcua
    pip install python-jose
    pip install pandas openpyxl
    pip install passlib
    pip install bcrypt
    pip install --upgrade pip
    ```

4. **Configurar la base de datos**:
    - Crea una base de datos en MySQL o PostgreSQL (según el que elijas).
    - Configura las credenciales de la base de datos en el archivo `config.py`.

    Ejemplo de configuración en `config.py`:
    ```python
    SQLALCHEMY_DATABASE_URL = "mysql+mysqlconnector://user:password@localhost/plc_data"
    ```

5. **Crear las tablas en la base de datos**:
    Ejecuta el siguiente comando para crear las tablas en la base de datos configurada:
    ```bash
    uvicorn main:app --reload
    ```

    Las tablas se crearán automáticamente al iniciar la aplicación si aún no existen.

6. **Configurar la conexión con el PLC**:
    - Asegúrate de que el PLC esté correctamente configurado y accesible a través de OPC-UA.
    - Configura la URL de conexión al PLC en el archivo `config.py`:
      ```python
      OPCUA_SERVER_URL = "opc.tcp://192.168.1.10:4840"
      ```

## Uso

Una vez que todo esté configurado, puedes comenzar a interactuar con la API REST para obtener datos del PLC y generar reportes.

### Endpoints disponibles

1. **Leer datos de un nodo del PLC**:
    ```http
    GET /read-node/{node_id}
    ```
    Lee el valor de un nodo específico del PLC.

    **Ejemplo**:
    ```bash
    curl -X 'GET' 'http://127.0.0.1:8000/read-node/2'
    ```

2. **Obtener todos los registros almacenados**:
    ```http
    GET /records
    ```
    Obtiene todos los registros almacenados en la base de datos.

    **Ejemplo**:
    ```bash
    curl -X 'GET' 'http://127.0.0.1:8000/records'
    ```

3. **Generar un reporte de los datos**:
    ```http
    GET /generate-report
    ```
    Genera un reporte de los datos almacenados en la base de datos.

    **Ejemplo**:
    ```bash
    curl -X 'GET' 'http://127.0.0.1:8000/generate-report'
    ```

## Arquitectura

- **FastAPI**: Framework que maneja la lógica de la API.
- **SQLAlchemy**: ORM que facilita la interacción con la base de datos.
- **OPC-UA**: Protocolo utilizado para la comunicación con el PLC.
- **Base de Datos**: MySQL/PostgreSQL para almacenar los datos históricos del PLC.

## Ejecución

Para ejecutar el servidor de la aplicación, usa el siguiente comando:

```bash
uvicorn main:app --reload
