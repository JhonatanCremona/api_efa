FROM python:3.12

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=America/Mexico_City
WORKDIR /app
COPY . .

RUN pip install "fastapi[standard]"
    pip install PyMySQL
    pip install sqlalchemy
    pip install cryptography
    pip install opcua
    pip install python-jose
    pip install pandas openpyxl
    pip install passlib
    pip install bcrypt
    pip install aiosmtplib
    pip install Pillow
RUN pip install --upgrade pip

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]