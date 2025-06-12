FROM python:3.12

WORKDIR /app

COPY . /app

RUN pip install opcua

EXPOSE 4840

# Comando por defecto
CMD ["python", "opc_server_efa.py"]