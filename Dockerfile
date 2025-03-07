FROM python:3.12
WORKDIR /app

COPY . .

RUN pip install "fastapi[standard]"
RUN pip install PyMySQL
RUN pip install sqlalchemy
RUN pip install cryptography
RUN pip install opcua
RUN pip install python-jose
RUN pip install pandas openpyxl
RUN pip install passlib
RUN pip install --upgrade pip

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]