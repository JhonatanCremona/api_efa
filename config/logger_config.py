import logging
import os
import json
from datetime import datetime

# Crear carpeta de logs si no existe
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Formatter en formato JSON
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "filename": record.filename,
            "line": record.lineno
        }
        return json.dumps(log_record)

# Logger principal
logger = logging.getLogger("app_logger")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    json_formatter = JsonFormatter()

    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)

    # Handler para archivo (escritura inmediata)
    file_handler = logging.FileHandler(os.path.join(log_dir, "app.log"), encoding="utf-8")
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)

# También redirigimos logs de Uvicorn al logger principal
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.handlers = logger.handlers
uvicorn_logger.setLevel(logging.INFO)

# Para otros loggers de Uvicorn (error, access)
logging.getLogger("uvicorn.error").handlers = logger.handlers
logging.getLogger("uvicorn.access").handlers = logger.handlers
logging.getLogger("uvicorn.info").handlers = logger.handlers
