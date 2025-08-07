import os
import logging
import json
from datetime import datetime, timedelta
import aiosmtplib
from email.message import EmailMessage
from export_excel import export_ciclodesmoldeo_to_excel
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("uvicorn")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRO_HORA_PATH = os.path.join(BASE_DIR, "registro-hora.json")
EXCEL_DIR = os.path.join(BASE_DIR, "registros-productividad")
EXCEL_PATH_TEMPLATE = os.path.join(EXCEL_DIR, "ciclodesmoldeo_{fecha}.xlsx")
CORREOS_EFA_PATH = os.path.join(EXCEL_DIR, "correos-efa.txt")
CORREOS_CREMINOX_PATH = os.path.join(EXCEL_DIR, "correos-creminox.txt")

EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_FROM = os.getenv("EMAIL_FROM")
MAILJET_SMTP_USER = os.getenv("MAILJET_SMTP_USER")
MAILJET_SMTP_PASS = os.getenv("MAILJET_SMTP_PASS")
START_DATE = os.getenv("START_DATE")

def get_registro():
    if os.path.exists(REGISTRO_HORA_PATH):
        with open(REGISTRO_HORA_PATH, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def set_registro(registro):
    with open(REGISTRO_HORA_PATH, "w", encoding="utf-8") as f:
        json.dump(registro, f)

def leer_correos_desde_archivos():
    correos = []
    
    try:
        if os.path.exists(CORREOS_EFA_PATH):
            with open(CORREOS_EFA_PATH, "r", encoding="utf-8") as f:
                contenido_efa = f.read().strip()
                if contenido_efa:
                    correos_efa = [email.strip() for email in contenido_efa.split('\n') if email.strip()]
                    correos.extend(correos_efa)
                    logger.info(f"Correos leídos de EFA: {correos_efa}")
    except Exception as e:
        logger.error(f"Error leyendo correos de EFA: {e}")
    
    try:
        if os.path.exists(CORREOS_CREMINOX_PATH):
            with open(CORREOS_CREMINOX_PATH, "r", encoding="utf-8") as f:
                contenido_creminox = f.read().strip()
                if contenido_creminox:
                    correos_creminox = [email.strip() for email in contenido_creminox.split('\n') if email.strip()]
                    correos.extend(correos_creminox)
                    logger.info(f"Correos leídos de Creminox: {correos_creminox}")
    except Exception as e:
        logger.error(f"Error leyendo correos de Creminox: {e}")
    
    if not correos and EMAIL_TO:
        correos = [EMAIL_TO]
        logger.info(f"No se encontraron correos en archivos, usando EMAIL_TO: {EMAIL_TO}")
    
    logger.info(f"Total de destinatarios: {correos}")
    return correos

def ensure_excel_dir():
    if not os.path.exists(EXCEL_DIR):
        os.makedirs(EXCEL_DIR)

def limpiar_excel_dir(max_archivos=7):
    archivos = [f for f in os.listdir(EXCEL_DIR) if f.endswith(".xlsx")]
    if len(archivos) > max_archivos:
        archivos_completos = [os.path.join(EXCEL_DIR, f) for f in archivos]
        archivos_completos.sort(key=os.path.getctime)
        while len(archivos_completos) > max_archivos:
            archivo_eliminar = archivos_completos.pop(0)
            try:
                os.remove(archivo_eliminar)
                logger.info(f"Archivo eliminado por límite: {archivo_eliminar}")
            except Exception as e:
                logger.error(f"No se pudo eliminar {archivo_eliminar}: {e}")

async def send_email_with_attachment(subject, body, to_emails, from_email, username, password, file_path=None):
    if isinstance(to_emails, str):
        to_emails = [to_emails]
    
    for to_email in to_emails:
        if file_path:
            logger.info(f"Preparando envío de email a {to_email} con archivo {file_path}")
        else:
            logger.info(f"Preparando envío de email a {to_email} sin archivo adjunto")
            
        message = EmailMessage()
        message["From"] = from_email
        message["To"] = to_email
        message["Subject"] = subject
        
        # Crear contenido HTML con la imagen de Creminox
        html_body = f"""
        <html>
        <body>
            <p>{body.replace(chr(10), '<br>')}</p>
            <img src="cid:creminox_logo" alt="Creminox Logo" style="max-width: 200px; height: auto;">
        </body>
        </html>
        """
        
        message.set_content(body)
        message.add_alternative(html_body, subtype='html')

        try:
            creminox_path = os.path.join(os.path.dirname(__file__), "static", "cremonarecort.png")
            if os.path.exists(creminox_path):
                with open(creminox_path, "rb") as img_file:
                    img_data = img_file.read()
                    message.get_payload()[1].add_related(
                        img_data,
                        maintype='image',
                        subtype='png',
                        cid='creminox_logo'
                    )
            else:
                pass
                #logger.warning(f"Imagen no encontrada: {creminox_path}")
        except Exception as e:
            pass
            #logger.error(f"Error embebiendo imagen: {e}")

        # Solo adjuntar archivo si se proporciona file_path
        if file_path:
            try:
                with open(file_path, "rb") as f:
                    file_data = f.read()
                    message.add_attachment(
                        file_data,
                        maintype="application",
                        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        filename=os.path.basename(file_path)
                    )
                logger.info("Archivo adjuntado correctamente.")
            except Exception as e:
                logger.error(f"Error adjuntando archivo: {e}")
                continue

        try:
            await aiosmtplib.send(
                message,
                hostname="in-v3.mailjet.com",
                port=587,
                start_tls=True,
                username=username,
                password=password,
            )
            logger.info(f"Correo enviado correctamente a {to_email}.")
        except Exception as e:
            logger.error(f"Error enviando correo a {to_email}: {e}")
            continue

def daterange(start_date, end_date):
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(n)

async def tarea_exportar_y_enviar():
    ensure_excel_dir()
    while True:
        registro = get_registro()
        try:
            fecha_inicio = datetime.strptime(START_DATE, "%Y-%m-%d").date()
        except Exception:
            logger.error("START_DATE inválido en .env. Debe ser YYYY-MM-DD.")
            return
        fecha_hoy = datetime.now().date()
        fecha_limite = fecha_hoy - timedelta(days=1)

        fecha_pendiente = None
        for fecha in daterange(fecha_inicio, fecha_limite):
            fecha_str = fecha.strftime("%Y-%m-%d")
            if not registro.get("enviados", {}).get(fecha_str):
                fecha_pendiente = fecha
                break

        if fecha_pendiente:
            fecha_str = fecha_pendiente.strftime("%Y-%m-%d")
            logger.info(f"No se ha enviado el Excel para {fecha_str}. Generando y enviando...")
            excel_path = EXCEL_PATH_TEMPLATE.format(fecha=fecha_str)
            
            try:
                # Intentar generar el Excel
                resultado_export = export_ciclodesmoldeo_to_excel(excel_path, fecha_str)
                limpiar_excel_dir(max_archivos=7)
                
                destinatarios = leer_correos_desde_archivos()
                subject = f"Celda de desmoldeo EFA | Informe de productividad {fecha_str}"
                
                if resultado_export:
                    # Hay datos - enviar con archivo adjunto
                    body = f"""Estimado/a,

Adjunto encontrará el reporte de productividad de la "Celda de Desmoldeo" para la fecha {fecha_str}.

El archivo incluye:
- Resumen de productividad por torre (Hoja n°1)
- Detalles de ciclos realizados (Hoja n°2)

Saludos cordiales."""
                    
                    await send_email_with_attachment(
                        subject=subject,
                        body=body,
                        to_emails=destinatarios,
                        from_email=EMAIL_FROM,
                        username=MAILJET_SMTP_USER,
                        password=MAILJET_SMTP_PASS,
                        file_path=excel_path
                    )
                else:
                    body = f"""Estimado/a,

No se registraron ciclos realizados por la "Celda de Desmoldeo" para la fecha {fecha_str}.

Saludos cordiales."""
                    
                    await send_email_with_attachment(
                        subject=subject,
                        body=body,
                        to_emails=destinatarios,
                        from_email=EMAIL_FROM,
                        username=MAILJET_SMTP_USER,
                        password=MAILJET_SMTP_PASS,
                        file_path=None
                    )
                
                # Marcar como enviado en ambos casos
                if "enviados" not in registro:
                    registro["enviados"] = {}
                registro["enviados"][fecha_str] = True
                set_registro(registro)
                logger.info(f"Registro de envío actualizado para {fecha_str}.")
                
            except Exception as e:
                logger.error(f"Error en la tarea de exportar y enviar para {fecha_str}: {e}")
        else:
            logger.info("No hay días pendientes de envío.")

        import asyncio
        await asyncio.sleep(30)