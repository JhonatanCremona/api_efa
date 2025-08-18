import os
import logging
import json
import asyncio
import socket
from datetime import datetime, timedelta
import aiosmtplib
from email.message import EmailMessage
from export_excel import export_ciclodesmoldeo_to_excel, export_ciclodesmoldeo_efa_to_excel
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("uvicorn")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRO_HORA_PATH = os.path.join(BASE_DIR, "registro-hora.json")
EXCEL_DIR = os.path.join(BASE_DIR, "registros-productividad")
EXCEL_PATH_TEMPLATE = os.path.join(EXCEL_DIR, "ciclodesmoldeo_{fecha}.xlsx")
EXCEL_EFA_PATH_TEMPLATE = os.path.join(EXCEL_DIR, "ciclodesmoldeo_efa_{fecha}.xlsx")
CORREOS_EFA_PATH = os.path.join(EXCEL_DIR, "correos-efa.txt")
CORREOS_CREMINOX_PATH = os.path.join(EXCEL_DIR, "correos-creminox.txt")
CORREOS_ADMIN_PATH = os.path.join(EXCEL_DIR, "correos-admin.txt")

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
    try:
        with open(REGISTRO_HORA_PATH, "w", encoding="utf-8") as f:
            json.dump(registro, f, indent=2)
        logger.debug(f"Registro actualizado exitosamente: {registro}")
    except Exception as e:
        logger.error(f"Error escribiendo registro: {e}")

def validar_y_limpiar_registro():
    """
    Valida y limpia el registro de envíos, eliminando entradas muy antiguas
    para evitar que el archivo crezca indefinidamente.
    """
    registro = get_registro()
    
    # Eliminar registros más antiguos que 30 días
    fecha_limite = datetime.now().date() - timedelta(days=30)
    eliminados_enviados = 0
    eliminados_intentos = 0
    
    # Limpiar enviados
    if "enviados" in registro:
        enviados_filtrados = {}
        for fecha_str, valor in registro["enviados"].items():
            try:
                fecha_registro = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                if fecha_registro >= fecha_limite:
                    enviados_filtrados[fecha_str] = valor
                else:
                    eliminados_enviados += 1
            except ValueError:
                # Formato de fecha inválido, eliminar entrada
                eliminados_enviados += 1
                continue
        
        registro["enviados"] = enviados_filtrados
    else:
        registro["enviados"] = {}
    
    # Limpiar intentos fallidos (estructura antigua)
    if "intentos_fallidos" in registro:
        intentos_filtrados = {}
        for fecha_str, info in registro["intentos_fallidos"].items():
            try:
                fecha_registro = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                if fecha_registro >= fecha_limite:
                    intentos_filtrados[fecha_str] = info
                else:
                    eliminados_intentos += 1
            except ValueError:
                # Formato de fecha inválido, eliminar entrada
                eliminados_intentos += 1
                continue
        
        registro["intentos_fallidos"] = intentos_filtrados
    
    # Limpiar correos fallidos (nueva estructura)
    if "correos_fallidos" in registro:
        correos_filtrados = {}
        for fecha_str, correos_info in registro["correos_fallidos"].items():
            try:
                fecha_registro = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                if fecha_registro >= fecha_limite:
                    correos_filtrados[fecha_str] = correos_info
                else:
                    eliminados_intentos += 1
            except ValueError:
                # Formato de fecha inválido, eliminar entrada
                eliminados_intentos += 1
                continue
        
        registro["correos_fallidos"] = correos_filtrados
    
    # Limpiar correos exitosos (nueva estructura)
    if "correos_exitosos" in registro:
        exitosos_filtrados = {}
        for fecha_str, correos_info in registro["correos_exitosos"].items():
            try:
                fecha_registro = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                if fecha_registro >= fecha_limite:
                    exitosos_filtrados[fecha_str] = correos_info
                else:
                    eliminados_enviados += 1
            except ValueError:
                # Formato de fecha inválido, eliminar entrada
                eliminados_enviados += 1
                continue
        
        registro["correos_exitosos"] = exitosos_filtrados
    
    if eliminados_enviados > 0 or eliminados_intentos > 0:
        logger.info(f"Limpieza de registro: eliminadas {eliminados_enviados} entradas enviadas y {eliminados_intentos} intentos fallidos antiguos")
        set_registro(registro)
    
    return registro

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

def leer_correos_efa():
    """Lee solo los correos del archivo correos-efa.txt"""
    correos_efa = []
    
    try:
        if os.path.exists(CORREOS_EFA_PATH):
            with open(CORREOS_EFA_PATH, "r", encoding="utf-8") as f:
                contenido_efa = f.read().strip()
                if contenido_efa:
                    correos_efa = [email.strip() for email in contenido_efa.split('\n') if email.strip()]
                    logger.info(f"Correos EFA: {correos_efa}")
    except Exception as e:
        logger.error(f"Error leyendo correos de EFA: {e}")
    
    return correos_efa

def leer_correos_creminox():
    """Lee solo los correos del archivo correos-creminox.txt"""
    correos_creminox = []
    
    try:
        if os.path.exists(CORREOS_CREMINOX_PATH):
            with open(CORREOS_CREMINOX_PATH, "r", encoding="utf-8") as f:
                contenido_creminox = f.read().strip()
                if contenido_creminox:
                    correos_creminox = [email.strip() for email in contenido_creminox.split('\n') if email.strip()]
                    logger.info(f"Correos Creminox: {correos_creminox}")
    except Exception as e:
        logger.error(f"Error leyendo correos de Creminox: {e}")
    
    return correos_creminox

def leer_correos_admin():
    """Lee solo los correos del archivo correos-admin.txt"""
    correos_admin = []
    
    try:
        if os.path.exists(CORREOS_ADMIN_PATH):
            with open(CORREOS_ADMIN_PATH, "r", encoding="utf-8") as f:
                contenido_admin = f.read().strip()
                if contenido_admin:
                    correos_admin = [email.strip() for email in contenido_admin.split('\n') if email.strip()]
                    logger.info(f"Correos Admin: {correos_admin}")
    except Exception as e:
        logger.error(f"Error leyendo correos de Admin: {e}")
    
    return correos_admin

def ensure_excel_dir():
    if not os.path.exists(EXCEL_DIR):
        os.makedirs(EXCEL_DIR)

def limpiar_excel_dir(max_archivos=17):
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

async def send_email_with_attachment(subject, body, to_emails, from_email, username, password, file_path=None, max_retries=2):
    """
    Envía correos con adjunto y retorna información sobre el éxito del envío.
    
    Returns:
        dict: {
            'success': bool,
            'sent_count': int,
            'failed_count': int,
            'errors': list,
            'sent_emails': list,
            'failed_emails': list  # Lista de tuplas (email, error_msg)
        }
    """
    if isinstance(to_emails, str):
        to_emails = [to_emails]
    
    # Validar configuración SMTP
    if not all([from_email, username, password]):
        error_msg = "Configuración SMTP incompleta. Verifique EMAIL_FROM, MAILJET_SMTP_USER y MAILJET_SMTP_PASS"
        logger.error(error_msg)
        return {
            'success': False,
            'sent_count': 0,
            'failed_count': len(to_emails),
            'errors': [error_msg],
            'sent_emails': [],
            'failed_emails': [(email, error_msg) for email in to_emails]
        }
    
    sent_count = 0
    failed_count = 0
    errors = []
    sent_emails = []
    failed_emails = []
    
    for to_email in to_emails:
        if file_path:
            logger.info(f"Preparando envío de email a {to_email} con archivo {file_path}")
        else:
            logger.info(f"Preparando envío de email a {to_email} sin archivo adjunto")
        
        # Validar email de destino
        if not to_email or "@" not in to_email:
            error_msg = f"Email inválido: {to_email}"
            logger.error(error_msg)
            errors.append(error_msg)
            failed_emails.append((to_email, error_msg))
            failed_count += 1
            continue
            
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
        except Exception as e:
            logger.warning(f"Error embebiendo imagen (no crítico): {e}")

        # Solo adjuntar archivo si se proporciona file_path
        if file_path:
            if not os.path.exists(file_path):
                error_msg = f"Archivo no encontrado: {file_path}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_emails.append((to_email, error_msg))
                failed_count += 1
                continue
                
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
                error_msg = f"Error adjuntando archivo {file_path}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_emails.append((to_email, error_msg))
                failed_count += 1
                continue

        # Intentar enviar con reintentos
        email_sent = False
        last_error = None
        
        for attempt in range(max_retries):
            try:
                await aiosmtplib.send(
                    message,
                    hostname="in-v3.mailjet.com",
                    port=587,
                    start_tls=True,
                    username=username,
                    password=password,
                    timeout=30  # Timeout de 30 segundos
                )
                logger.info(f"Correo enviado correctamente a {to_email}.")
                email_sent = True
                sent_count += 1
                sent_emails.append(to_email)
                break
                
            except (aiosmtplib.SMTPException, ConnectionError, OSError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # Espera incremental: 5s, 10s, 15s
                    logger.warning(f"Error enviando correo a {to_email} (intento {attempt + 1}/{max_retries}): {e}. Reintentando en {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    error_msg = f"Error enviando correo a {to_email} después de {max_retries} intentos: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    failed_emails.append((to_email, error_msg))
                    failed_count += 1
            except Exception as e:
                # Error no relacionado con red/SMTP, no reintentar
                error_msg = f"Error crítico enviando correo a {to_email}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_emails.append((to_email, error_msg))
                failed_count += 1
                break
    
    success = failed_count == 0
    
    return {
        'success': success,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'errors': errors,
        'sent_emails': sent_emails,
        'failed_emails': failed_emails
    }

async def send_email_with_multiple_attachments(subject, body, to_emails, from_email, username, password, file_paths=None, max_retries=2):
    """
    Función para enviar correos con múltiples archivos adjuntos
    
    Returns:
        dict: {
            'success': bool,
            'sent_count': int,
            'failed_count': int,
            'errors': list,
            'sent_emails': list,
            'failed_emails': list  # Lista de tuplas (email, error_msg)
        }
    """
    if isinstance(to_emails, str):
        to_emails = [to_emails]
    
    # Validar configuración SMTP
    if not all([from_email, username, password]):
        error_msg = "Configuración SMTP incompleta. Verifique EMAIL_FROM, MAILJET_SMTP_USER y MAILJET_SMTP_PASS"
        logger.error(error_msg)
        return {
            'success': False,
            'sent_count': 0,
            'failed_count': len(to_emails),
            'errors': [error_msg],
            'sent_emails': [],
            'failed_emails': [(email, error_msg) for email in to_emails]
        }
    
    sent_count = 0
    failed_count = 0
    errors = []
    sent_emails = []
    failed_emails = []
    
    for to_email in to_emails:
        if file_paths:
            logger.info(f"Preparando envío de email a {to_email} con {len(file_paths)} archivos adjuntos")
        else:
            logger.info(f"Preparando envío de email a {to_email} sin archivos adjuntos")
        
        # Validar email de destino
        if not to_email or "@" not in to_email:
            error_msg = f"Email inválido: {to_email}"
            logger.error(error_msg)
            errors.append(error_msg)
            failed_emails.append((to_email, error_msg))
            failed_count += 1
            continue
            
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
        except Exception as e:
            logger.warning(f"Error embebiendo imagen (no crítico): {e}")

        # Adjuntar múltiples archivos si se proporcionan
        attachment_errors = []
        if file_paths:
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    attachment_error = f"Archivo no encontrado: {file_path}"
                    logger.warning(attachment_error)
                    attachment_errors.append(attachment_error)
                    continue
                    
                try:
                    with open(file_path, "rb") as f:
                        file_data = f.read()
                        message.add_attachment(
                            file_data,
                            maintype="application",
                            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            filename=os.path.basename(file_path)
                        )
                    logger.info(f"Archivo adjuntado correctamente: {os.path.basename(file_path)}")
                except Exception as e:
                    attachment_error = f"Error adjuntando archivo {file_path}: {e}"
                    logger.error(attachment_error)
                    attachment_errors.append(attachment_error)
                    
        # Si todos los archivos fallaron, marcar como error
        if file_paths and len(attachment_errors) == len(file_paths):
            error_msg = f"No se pudo adjuntar ningún archivo para {to_email}: {'; '.join(attachment_errors)}"
            logger.error(error_msg)
            errors.append(error_msg)
            failed_emails.append((to_email, error_msg))
            failed_count += 1
            continue

        # Intentar enviar con reintentos
        email_sent = False
        last_error = None
        
        for attempt in range(max_retries):
            try:
                await aiosmtplib.send(
                    message,
                    hostname="in-v3.mailjet.com",
                    port=587,
                    start_tls=True,
                    username=username,
                    password=password,
                    timeout=30  # Timeout de 30 segundos
                )
                logger.info(f"Correo enviado correctamente a {to_email}.")
                email_sent = True
                sent_count += 1
                sent_emails.append(to_email)
                # Si hubo errores de adjuntos pero el email se envió, registrar advertencia
                if attachment_errors:
                    logger.warning(f"Correo enviado a {to_email} pero con algunos errores de archivos adjuntos: {'; '.join(attachment_errors)}")
                break
                
            except (aiosmtplib.SMTPException, ConnectionError, OSError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # Espera incremental: 5s, 10s, 15s
                    logger.warning(f"Error enviando correo a {to_email} (intento {attempt + 1}/{max_retries}): {e}. Reintentando en {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    error_msg = f"Error enviando correo a {to_email} después de {max_retries} intentos: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    failed_emails.append((to_email, error_msg))
                    failed_count += 1
            except Exception as e:
                # Error no relacionado con red/SMTP, no reintentar
                error_msg = f"Error crítico enviando correo a {to_email}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_emails.append((to_email, error_msg))
                failed_count += 1
                break
    
    success = failed_count == 0
    
    return {
        'success': success,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'errors': errors,
        'sent_emails': sent_emails,
        'failed_emails': failed_emails
    }

def daterange(start_date, end_date):
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(n)

async def verificar_conectividad_smtp(hostname="in-v3.mailjet.com", port=587, timeout=5):
    """
    Verifica si hay conectividad con el servidor SMTP.
    
    Returns:
        bool: True si hay conectividad, False en caso contrario
    """
    try:
        # Verificar conectividad básica TCP
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(hostname, port),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        logger.info(f"Conectividad SMTP verificada exitosamente con {hostname}:{port}")
        return True
    except (OSError, asyncio.TimeoutError, ConnectionRefusedError) as e:
        logger.warning(f"No hay conectividad con el servidor SMTP {hostname}:{port}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error inesperado verificando conectividad SMTP: {e}")
        return False

async def verificar_conectividad_internet():
    """
    Verifica conectividad básica a internet probando con varios servidores DNS.
    
    Returns:
        bool: True si hay conectividad, False en caso contrario
    """
    servidores_test = [
        ("8.8.8.8", 53),      # Google DNS
        ("1.1.1.1", 53),      # Cloudflare DNS
        ("208.67.222.222", 53) # OpenDNS
    ]
    
    for host, port in servidores_test:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=3
            )
            writer.close()
            await writer.wait_closed()
            logger.info(f"Conectividad a internet verificada usando {host}")
            return True
        except:
            continue
    
    logger.warning("No se pudo verificar conectividad a internet")
    return False

def filtrar_correos_pendientes(correos, fecha_str, registro, tipo_grupo):
    """
    Filtra los correos que necesitan ser enviados, excluyendo los que ya fueron enviados exitosamente.
    
    Args:
        correos: Lista de emails del grupo
        fecha_str: Fecha en formato YYYY-MM-DD
        registro: Diccionario del registro
        tipo_grupo: String identificando el tipo (efa/creminox/admin)
    
    Returns:
        Lista de correos que necesitan ser enviados
    """
    if not correos:
        return []
    
    correos_pendientes = []
    
    for correo in correos:
        correo_key = f"{tipo_grupo}:{correo}"
        
        # Verificar si ya fue enviado exitosamente
        ya_enviado = False
        if "correos_exitosos" in registro and fecha_str in registro["correos_exitosos"]:
            if correo_key in registro["correos_exitosos"][fecha_str]:
                ya_enviado = True
                logger.debug(f"⚡ Saltando {correo} - ya enviado exitosamente")
        
        # Si no fue enviado exitosamente, verificar si debe ser reenviado
        if not ya_enviado:
            # Verificar si está en fallidos y si es momento de reintentar
            debe_enviar = True
            if "correos_fallidos" in registro and fecha_str in registro["correos_fallidos"]:
                if correo_key in registro["correos_fallidos"][fecha_str]:
                    info_correo = registro["correos_fallidos"][fecha_str][correo_key]
                    if "proximo_intento" in info_correo:
                        try:
                            proximo_intento = datetime.fromisoformat(info_correo["proximo_intento"])
                            if datetime.now() < proximo_intento:
                                debe_enviar = False
                                logger.debug(f"⏰ Saltando {correo} - próximo intento: {proximo_intento}")
                        except (ValueError, TypeError):
                            # Error en formato, permitir envío
                            pass
            
            if debe_enviar:
                correos_pendientes.append(correo)
                logger.debug(f"📋 Agregando {correo} a pendientes")
    
    return correos_pendientes

def verificar_correos_restantes(correos, fecha_str, registro, tipo_grupo):
    """
    Verifica qué correos aún NO han sido enviados exitosamente para una fecha.
    
    Args:
        correos: Lista de emails del grupo
        fecha_str: Fecha en formato YYYY-MM-DD
        registro: Diccionario del registro
        tipo_grupo: String identificando el tipo (efa/creminox/admin)
    
    Returns:
        Lista de correos que aún no han sido enviados exitosamente
    """
    if not correos:
        return []
    
    correos_restantes = []
    
    # Verificar cada correo configurado
    for correo in correos:
        correo_key = f"{tipo_grupo}:{correo}"
        
        # Verificar si está en la lista de exitosos
        correo_enviado = False
        if "correos_exitosos" in registro and fecha_str in registro["correos_exitosos"]:
            if correo_key in registro["correos_exitosos"][fecha_str]:
                correo_enviado = True
                logger.debug(f"✅ {correo} ya fue enviado exitosamente")
        
        # Si no fue enviado exitosamente, agregarlo a la lista de restantes
        if not correo_enviado:
            correos_restantes.append(correo)
            logger.debug(f"⏳ {correo} aún no ha sido enviado")
    
    return correos_restantes

def registrar_correos_exitosos(correos_enviados, fecha_str, registro, tipo_grupo):
    """
    Registra los correos que se enviaron exitosamente para evitar reenvíos.
    
    Args:
        correos_enviados: Lista de emails enviados exitosamente
        fecha_str: Fecha en formato YYYY-MM-DD
        registro: Diccionario del registro
        tipo_grupo: String identificando el tipo (efa/creminox/admin)
    """
    if not correos_enviados:
        return
    
    # Crear registro de correos enviados exitosamente
    if "correos_exitosos" not in registro:
        registro["correos_exitosos"] = {}
    
    if fecha_str not in registro["correos_exitosos"]:
        registro["correos_exitosos"][fecha_str] = {}
    
    # Registrar cada correo exitoso
    for correo in correos_enviados:
        correo_key = f"{tipo_grupo}:{correo}"
        registro["correos_exitosos"][fecha_str][correo_key] = {
            "enviado_en": datetime.now().isoformat(),
            "tipo_grupo": tipo_grupo
        }
        logger.debug(f"✅ Registrado como exitoso: {correo_key} para {fecha_str}")
    
    # Limpiar correos exitosos de la lista de fallidos
    if "correos_fallidos" in registro and fecha_str in registro["correos_fallidos"]:
        for correo in correos_enviados:
            correo_key = f"{tipo_grupo}:{correo}"
            if correo_key in registro["correos_fallidos"][fecha_str]:
                del registro["correos_fallidos"][fecha_str][correo_key]
                logger.debug(f"🗑️ Eliminado de fallidos: {correo_key}")
        
        # Si no quedan correos fallidos para esta fecha, limpiar la entrada
        if not registro["correos_fallidos"][fecha_str]:
            del registro["correos_fallidos"][fecha_str]

def registrar_correos_fallidos(correos_fallidos_info, fecha_str, registro, tipo_grupo):
    """
    Registra los correos que fallaron para programar reintentos.
    
    Args:
        correos_fallidos_info: Lista de tuplas (email, error_msg)
        fecha_str: Fecha en formato YYYY-MM-DD
        registro: Diccionario del registro
        tipo_grupo: String identificando el tipo (efa/creminox/admin)
    """
    if not correos_fallidos_info:
        return
    
    if "correos_fallidos" not in registro:
        registro["correos_fallidos"] = {}
    
    if fecha_str not in registro["correos_fallidos"]:
        registro["correos_fallidos"][fecha_str] = {}
    
    for correo, error_msg in correos_fallidos_info:
        correo_key = f"{tipo_grupo}:{correo}"
        
        if correo_key not in registro["correos_fallidos"][fecha_str]:
            registro["correos_fallidos"][fecha_str][correo_key] = {
                "contador": 0,
                "ultimo_intento": None,
                "proximo_intento": None,
                "ultimo_error": None
            }
        
        info_correo = registro["correos_fallidos"][fecha_str][correo_key]
        info_correo["contador"] += 1
        info_correo["ultimo_intento"] = datetime.now().isoformat()
        info_correo["ultimo_error"] = error_msg
        
        # Calcular próximo intento con backoff exponencial (más agresivo para evitar saturación)
        intentos = info_correo["contador"]
        if intentos <= 2:
            delay_minutos = 60  # 1 hora
        elif intentos <= 3:
            delay_minutos = 180  # 3 horas
        elif intentos <= 4:
            delay_minutos = 360  # 6 horas
        else:
            delay_minutos = 720  # 12 horas
        
        proximo_intento = datetime.now() + timedelta(minutes=delay_minutos)
        info_correo["proximo_intento"] = proximo_intento.isoformat()
        
        logger.error(f"❌ Error en envío a {correo} para {fecha_str} (intento #{intentos}). Próximo intento: {proximo_intento.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # LÍMITE MÁXIMO MÁS RESTRICTIVO para evitar saturación del sistema
        if intentos >= 5:
            logger.warning(f"⚠️ Máximo de 5 intentos alcanzado para {correo} en {fecha_str}. Eliminando de reintentos para evitar saturación del sistema.")
            del registro["correos_fallidos"][fecha_str][correo_key]

async def tarea_exportar_y_enviar():
    ensure_excel_dir()
    
    # LÍMITES DE PROTECCIÓN CONTRA SATURACIÓN
    MAX_CORREOS_POR_CICLO = 20  # Máximo de correos a procesar por ciclo
    MAX_FECHAS_PENDIENTES = 5   # Máximo de fechas con correos pendientes
    
    while True:
        # Validar y limpiar registro al inicio de cada ciclo
        registro = validar_y_limpiar_registro()
        
        try:
            fecha_inicio = datetime.strptime(START_DATE, "%Y-%m-%d").date()
        except Exception:
            logger.error("START_DATE inválido en .env. Debe ser YYYY-MM-DD.")
            return
        fecha_hoy = datetime.now().date()
        fecha_limite = fecha_hoy - timedelta(days=1)

        # Contar correos pendientes totales para evitar saturación
        total_correos_pendientes = 0
        fechas_con_pendientes = 0
        
        if "correos_fallidos" in registro:
            for fecha_str, correos_info in registro["correos_fallidos"].items():
                if correos_info:  # Si hay correos fallidos en esta fecha
                    fechas_con_pendientes += 1
                    total_correos_pendientes += len(correos_info)
        
        # PROTECCIÓN: Si hay demasiados correos pendientes, aumentar el intervalo de espera
        if total_correos_pendientes > MAX_CORREOS_POR_CICLO:
            logger.warning(f"⚠️ Demasiados correos pendientes ({total_correos_pendientes}). Aumentando intervalo de espera para evitar saturación.")
            await asyncio.sleep(300)  # Esperar 5 minutos en lugar de 30 segundos
            continue
            
        if fechas_con_pendientes > MAX_FECHAS_PENDIENTES:
            logger.warning(f"⚠️ Demasiadas fechas con correos pendientes ({fechas_con_pendientes}). Aumentando intervalo de espera.")
            await asyncio.sleep(300)  # Esperar 5 minutos
            continue

        fecha_pendiente = None
        for fecha in daterange(fecha_inicio, fecha_limite):
            fecha_str = fecha.strftime("%Y-%m-%d")
            
            # Verificar si ya está marcado como enviado completamente
            if registro.get("enviados", {}).get(fecha_str):
                continue
            
            # Verificar si hay correos específicos pendientes de reenvío
            correos_pendientes = False
            if "correos_fallidos" in registro and fecha_str in registro["correos_fallidos"]:
                # Verificar si es momento de reintentar algún correo fallido
                for email, info in registro["correos_fallidos"][fecha_str].items():
                    if "proximo_intento" in info:
                        try:
                            proximo_intento = datetime.fromisoformat(info["proximo_intento"])
                            if datetime.now() >= proximo_intento:
                                correos_pendientes = True
                                break
                        except (ValueError, TypeError):
                            # Error en el formato de fecha, permitir reintento
                            correos_pendientes = True
                            break
                    else:
                        correos_pendientes = True
                        break
            else:
                # Primera vez que se procesa esta fecha
                correos_pendientes = True
            
            if correos_pendientes:
                fecha_pendiente = fecha
                break

        if fecha_pendiente:
            fecha_str = fecha_pendiente.strftime("%Y-%m-%d")
            
            # Mostrar información del intento
            if "correos_fallidos" in registro and fecha_str in registro["correos_fallidos"]:
                correos_pendientes = len(registro["correos_fallidos"][fecha_str])
                logger.info(f"🔄 Reintentando envío para {fecha_str} ({correos_pendientes} correos pendientes)")
            else:
                logger.info(f"📧 Primer intento de envío para {fecha_str}")
                
            logger.info(f"Generando y enviando reportes para {fecha_str}...")
            
            # Verificar conectividad antes de intentar enviar
            logger.info("Verificando conectividad...")
            tiene_internet = await verificar_conectividad_internet()
            tiene_smtp = await verificar_conectividad_smtp()
            
            if not tiene_internet:
                logger.warning(f"No hay conectividad a internet. Se intentará enviar {fecha_str} en el próximo ciclo.")
                await asyncio.sleep(60)
                continue
                
            if not tiene_smtp:
                logger.warning(f"No hay conectividad con el servidor SMTP. Se intentará enviar {fecha_str} en el próximo ciclo.")
                await asyncio.sleep(60)
                continue
            
            # Rutas de los archivos Excel
            excel_creminox_path = EXCEL_PATH_TEMPLATE.format(fecha=fecha_str)
            excel_efa_path = EXCEL_EFA_PATH_TEMPLATE.format(fecha=fecha_str)
            
            try:
                # Generar ambos archivos Excel
                logger.info("Generando archivo Excel completo para Creminox...")
                resultado_export_creminox = export_ciclodesmoldeo_to_excel(excel_creminox_path, fecha_str)
                
                logger.info("Generando archivo Excel simplificado para EFA...")
                resultado_export_efa = export_ciclodesmoldeo_efa_to_excel(excel_efa_path, fecha_str)
                
                # Limpiar directorio (máximo 17 archivos)
                limpiar_excel_dir(max_archivos=17)
                
                # Leer correos por separado y filtrar los que necesitan ser enviados
                correos_efa = leer_correos_efa()
                correos_creminox = leer_correos_creminox()
                correos_admin = leer_correos_admin()
                
                # Filtrar correos que ya fueron enviados exitosamente
                correos_efa_pendientes = filtrar_correos_pendientes(correos_efa, fecha_str, registro, "efa")
                correos_creminox_pendientes = filtrar_correos_pendientes(correos_creminox, fecha_str, registro, "creminox")
                correos_admin_pendientes = filtrar_correos_pendientes(correos_admin, fecha_str, registro, "admin")
                
                # PROTECCIÓN ADICIONAL: Limitar correos por envío para evitar saturación
                MAX_CORREOS_POR_GRUPO = 5
                if len(correos_efa_pendientes) > MAX_CORREOS_POR_GRUPO:
                    logger.warning(f"⚠️ Limitando correos EFA de {len(correos_efa_pendientes)} a {MAX_CORREOS_POR_GRUPO} para evitar saturación")
                    correos_efa_pendientes = correos_efa_pendientes[:MAX_CORREOS_POR_GRUPO]
                
                if len(correos_creminox_pendientes) > MAX_CORREOS_POR_GRUPO:
                    logger.warning(f"⚠️ Limitando correos Creminox de {len(correos_creminox_pendientes)} a {MAX_CORREOS_POR_GRUPO} para evitar saturación")
                    correos_creminox_pendientes = correos_creminox_pendientes[:MAX_CORREOS_POR_GRUPO]
                
                if len(correos_admin_pendientes) > MAX_CORREOS_POR_GRUPO:
                    logger.warning(f"⚠️ Limitando correos Admin de {len(correos_admin_pendientes)} a {MAX_CORREOS_POR_GRUPO} para evitar saturación")
                    correos_admin_pendientes = correos_admin_pendientes[:MAX_CORREOS_POR_GRUPO]
                
                # Verificar que hay al menos un destinatario válido
                total_destinatarios = len(correos_efa_pendientes) + len(correos_creminox_pendientes) + len(correos_admin_pendientes)
                if total_destinatarios == 0:
                    logger.info(f"No hay correos pendientes para {fecha_str}. Marcando como enviado completamente.")
                    if "enviados" not in registro:
                        registro["enviados"] = {}
                    registro["enviados"][fecha_str] = True
                    
                    # Limpiar correos fallidos ya que no hay más pendientes
                    if "correos_fallidos" in registro and fecha_str in registro["correos_fallidos"]:
                        del registro["correos_fallidos"][fecha_str]
                    
                    set_registro(registro)
                    await asyncio.sleep(60)
                    continue
                
                logger.info(f"Correos pendientes - EFA: {len(correos_efa_pendientes)}, Creminox: {len(correos_creminox_pendientes)}, Admin: {len(correos_admin_pendientes)}")
                
                subject = f"Celda de desmoldeo EFA | Informe de productividad {fecha_str}"
                
                if resultado_export_creminox and resultado_export_efa:
                    # Hay datos - enviar correos con archivos correspondientes
                    
                    # 1. Enviar a correos EFA pendientes (solo archivo EFA simplificado)
                    if correos_efa_pendientes:
                        body_efa = f"""Estimado/a,

Adjunto encontrará el reporte de productividad de la "Celda de Desmoldeo" para la fecha {fecha_str}.

El archivo incluye:
- Resumen de productividad por torre (Hoja n°1)
- Detalles de ciclos realizados (Hoja n°2)

Saludos cordiales."""
                        
                        resultado_efa = await send_email_with_attachment(
                            subject=subject,
                            body=body_efa,
                            to_emails=correos_efa_pendientes,
                            from_email=EMAIL_FROM,
                            username=MAILJET_SMTP_USER,
                            password=MAILJET_SMTP_PASS,
                            file_path=excel_efa_path
                        )
                        
                        # Registrar resultados específicos por correo
                        if resultado_efa['sent_emails']:
                            registrar_correos_exitosos(resultado_efa['sent_emails'], fecha_str, registro, "efa")
                            logger.info(f"✅ Correos EFA enviados exitosamente: {resultado_efa['sent_emails']}")
                        
                        if resultado_efa['failed_emails']:
                            registrar_correos_fallidos(resultado_efa['failed_emails'], fecha_str, registro, "efa")
                            logger.error(f"❌ Correos EFA fallidos: {[email for email, _ in resultado_efa['failed_emails']]}")
                    
                    # 2. Enviar a correos Creminox pendientes (solo archivo completo)
                    if correos_creminox_pendientes:
                        body_creminox = f"""Estimado/a,

Adjunto encontrará el reporte completo de productividad de la "Celda de Desmoldeo" para la fecha {fecha_str}.

El archivo incluye:
- Resumen de productividad por torre (Hoja n°1)
- Detalles de ciclos realizados (Hoja n°2)

Saludos cordiales."""
                        
                        resultado_creminox = await send_email_with_attachment(
                            subject=subject,
                            body=body_creminox,
                            to_emails=correos_creminox_pendientes,
                            from_email=EMAIL_FROM,
                            username=MAILJET_SMTP_USER,
                            password=MAILJET_SMTP_PASS,
                            file_path=excel_creminox_path
                        )
                        
                        # Registrar resultados específicos por correo
                        if resultado_creminox['sent_emails']:
                            registrar_correos_exitosos(resultado_creminox['sent_emails'], fecha_str, registro, "creminox")
                            logger.info(f"✅ Correos Creminox enviados exitosamente: {resultado_creminox['sent_emails']}")
                        
                        if resultado_creminox['failed_emails']:
                            registrar_correos_fallidos(resultado_creminox['failed_emails'], fecha_str, registro, "creminox")
                            logger.error(f"❌ Correos Creminox fallidos: {[email for email, _ in resultado_creminox['failed_emails']]}")
                    
                    # 3. Enviar a correos Admin pendientes (ambos archivos)
                    if correos_admin_pendientes:
                        body_admin = f"""Estimado/a,

Adjunto encontrará los reportes de productividad de la "Celda de Desmoldeo" para la fecha {fecha_str}.

Los archivos incluyen:
- Reporte completo de ingeniería con todas las métricas (Archivo 1)
- Reporte simplificado para cliente (Archivo 2)

Saludos cordiales."""
                        
                        resultado_admin = await send_email_with_multiple_attachments(
                            subject=subject,
                            body=body_admin,
                            to_emails=correos_admin_pendientes,
                            from_email=EMAIL_FROM,
                            username=MAILJET_SMTP_USER,
                            password=MAILJET_SMTP_PASS,
                            file_paths=[excel_creminox_path, excel_efa_path]
                        )
                        
                        # Registrar resultados específicos por correo
                        if resultado_admin['sent_emails']:
                            registrar_correos_exitosos(resultado_admin['sent_emails'], fecha_str, registro, "admin")
                            logger.info(f"✅ Correos Admin enviados exitosamente: {resultado_admin['sent_emails']}")
                        
                        if resultado_admin['failed_emails']:
                            registrar_correos_fallidos(resultado_admin['failed_emails'], fecha_str, registro, "admin")
                            logger.error(f"❌ Correos Admin fallidos: {[email for email, _ in resultado_admin['failed_emails']]}")
                    
                elif resultado_export_creminox and not resultado_export_efa:
                    # Solo hay datos en el archivo de Creminox (caso improbable)
                    logger.warning("Solo se generó el archivo de Creminox, no el de EFA")
                    
                    # Enviar archivo completo a Creminox y Admin pendientes
                    if correos_creminox_pendientes:
                        body_creminox = f"""Estimado/a,

Adjunto encontrará el reporte de productividad de la "Celda de Desmoldeo" para la fecha {fecha_str}.

Nota: Hubo un problema al generar el reporte simplificado.

Saludos cordiales."""
                        
                        resultado_creminox = await send_email_with_attachment(
                            subject=subject,
                            body=body_creminox,
                            to_emails=correos_creminox_pendientes,
                            from_email=EMAIL_FROM,
                            username=MAILJET_SMTP_USER,
                            password=MAILJET_SMTP_PASS,
                            file_path=excel_creminox_path
                        )
                        
                        if resultado_creminox['sent_emails']:
                            registrar_correos_exitosos(resultado_creminox['sent_emails'], fecha_str, registro, "creminox")
                            logger.info(f"✅ Correos Creminox enviados exitosamente: {resultado_creminox['sent_emails']}")
                        
                        if resultado_creminox['failed_emails']:
                            registrar_correos_fallidos(resultado_creminox['failed_emails'], fecha_str, registro, "creminox")
                    
                    if correos_admin_pendientes:
                        resultado_admin = await send_email_with_attachment(
                            subject=subject,
                            body=body_creminox,
                            to_emails=correos_admin_pendientes,
                            from_email=EMAIL_FROM,
                            username=MAILJET_SMTP_USER,
                            password=MAILJET_SMTP_PASS,
                            file_path=excel_creminox_path
                        )
                        
                        if resultado_admin['sent_emails']:
                            registrar_correos_exitosos(resultado_admin['sent_emails'], fecha_str, registro, "admin")
                            logger.info(f"✅ Correos Admin enviados exitosamente: {resultado_admin['sent_emails']}")
                        
                        if resultado_admin['failed_emails']:
                            registrar_correos_fallidos(resultado_admin['failed_emails'], fecha_str, registro, "admin")
                    
                    # Enviar correo sin archivo a EFA pendientes
                    if correos_efa_pendientes:
                        body_sin_datos = f"""Estimado/a,

No se pudieron generar los reportes de productividad de la "Celda de Desmoldeo" para la fecha {fecha_str} debido a un error técnico.

Saludos cordiales."""
                        
                        resultado_efa = await send_email_with_attachment(
                            subject=subject,
                            body=body_sin_datos,
                            to_emails=correos_efa_pendientes,
                            from_email=EMAIL_FROM,
                            username=MAILJET_SMTP_USER,
                            password=MAILJET_SMTP_PASS,
                            file_path=None
                        )
                        
                        if resultado_efa['sent_emails']:
                            registrar_correos_exitosos(resultado_efa['sent_emails'], fecha_str, registro, "efa")
                            logger.info(f"✅ Correos EFA (sin datos) enviados exitosamente: {resultado_efa['sent_emails']}")
                        
                        if resultado_efa['failed_emails']:
                            registrar_correos_fallidos(resultado_efa['failed_emails'], fecha_str, registro, "efa")
                        
                else:
                    # No hay datos - enviar correos sin archivos adjuntos a todos los pendientes
                    body_sin_datos = f"""Estimado/a,

No se registraron ciclos realizados por la "Celda de Desmoldeo" para la fecha {fecha_str}.

Saludos cordiales."""
                    
                    # Combinar todos los correos pendientes
                    todos_correos_pendientes = correos_efa_pendientes + correos_creminox_pendientes + correos_admin_pendientes
                    
                    if todos_correos_pendientes:
                        resultado_sin_datos = await send_email_with_attachment(
                            subject=subject,
                            body=body_sin_datos,
                            to_emails=todos_correos_pendientes,
                            from_email=EMAIL_FROM,
                            username=MAILJET_SMTP_USER,
                            password=MAILJET_SMTP_PASS,
                            file_path=None
                        )
                        
                        # Registrar exitosos por grupo
                        for correo in resultado_sin_datos['sent_emails']:
                            if correo in correos_efa_pendientes:
                                registrar_correos_exitosos([correo], fecha_str, registro, "efa")
                            elif correo in correos_creminox_pendientes:
                                registrar_correos_exitosos([correo], fecha_str, registro, "creminox")
                            elif correo in correos_admin_pendientes:
                                registrar_correos_exitosos([correo], fecha_str, registro, "admin")
                        
                        # Registrar fallidos por grupo
                        for correo, error in resultado_sin_datos['failed_emails']:
                            if correo in correos_efa_pendientes:
                                registrar_correos_fallidos([(correo, error)], fecha_str, registro, "efa")
                            elif correo in correos_creminox_pendientes:
                                registrar_correos_fallidos([(correo, error)], fecha_str, registro, "creminox")
                            elif correo in correos_admin_pendientes:
                                registrar_correos_fallidos([(correo, error)], fecha_str, registro, "admin")
                        
                        if resultado_sin_datos['sent_emails']:
                            logger.info(f"✅ Correos sin datos enviados exitosamente: {resultado_sin_datos['sent_emails']}")
                        if resultado_sin_datos['failed_emails']:
                            logger.error(f"❌ Correos sin datos fallidos: {[email for email, _ in resultado_sin_datos['failed_emails']]}")
                    else:
                        logger.info("No hay correos pendientes para enviar.")
                
                # Verificar si todos los correos configurados han sido enviados exitosamente
                correos_restantes_efa = verificar_correos_restantes(correos_efa, fecha_str, registro, "efa")
                correos_restantes_creminox = verificar_correos_restantes(correos_creminox, fecha_str, registro, "creminox")
                correos_restantes_admin = verificar_correos_restantes(correos_admin, fecha_str, registro, "admin")
                
                # DEBUG: Mostrar el estado de los correos
                logger.debug(f"DEBUG {fecha_str} - EFA configurados: {correos_efa}, restantes: {correos_restantes_efa}")
                logger.debug(f"DEBUG {fecha_str} - Creminox configurados: {correos_creminox}, restantes: {correos_restantes_creminox}")
                logger.debug(f"DEBUG {fecha_str} - Admin configurados: {correos_admin}, restantes: {correos_restantes_admin}")
                
                total_correos_restantes = len(correos_restantes_efa) + len(correos_restantes_creminox) + len(correos_restantes_admin)
                
                if total_correos_restantes == 0:
                    # Todos los correos fueron enviados exitosamente
                    if "enviados" not in registro:
                        registro["enviados"] = {}
                    registro["enviados"][fecha_str] = True
                    
                    # Limpiar correos fallidos ya que todos fueron enviados
                    if "correos_fallidos" in registro and fecha_str in registro["correos_fallidos"]:
                        del registro["correos_fallidos"][fecha_str]
                    
                    # Limpiar correos exitosos ya que la fecha está completada
                    if "correos_exitosos" in registro and fecha_str in registro["correos_exitosos"]:
                        del registro["correos_exitosos"][fecha_str]
                    
                    set_registro(registro)
                    logger.info(f"✅ Todos los correos enviados exitosamente para {fecha_str} - MARCADO COMO COMPLETADO.")
                else:
                    # Aún hay correos pendientes, guardar el estado actual
                    set_registro(registro)
                    logger.info(f"⏳ Quedan {total_correos_restantes} correos pendientes para {fecha_str}:")
                    if correos_restantes_efa:
                        logger.info(f"  📧 EFA pendientes: {correos_restantes_efa}")
                    if correos_restantes_creminox:
                        logger.info(f"  📧 Creminox pendientes: {correos_restantes_creminox}")
                    if correos_restantes_admin:
                        logger.info(f"  📧 Admin pendientes: {correos_restantes_admin}")
                    logger.info(f"  🔄 Se reintentarán más tarde.")
                
            except Exception as e:
                logger.error(f"💥 Error crítico en la tarea de exportar y enviar para {fecha_str}: {e}")
                
                # Para errores críticos que impiden generar archivos, marcar todos los correos pendientes como fallidos temporalmente
                if "correos_fallidos" not in registro:
                    registro["correos_fallidos"] = {}
                
                if fecha_str not in registro["correos_fallidos"]:
                    registro["correos_fallidos"][fecha_str] = {}
                
                # Marcar todos los correos configurados como fallidos con error crítico
                todos_correos = correos_efa + correos_creminox + correos_admin
                error_critico = f"Error crítico generando archivos: {e}"
                
                for correo in correos_efa:
                    correo_key = f"efa:{correo}"
                    if correo_key not in registro["correos_fallidos"][fecha_str]:
                        registro["correos_fallidos"][fecha_str][correo_key] = {"contador": 0}
                    
                    info_correo = registro["correos_fallidos"][fecha_str][correo_key]
                    info_correo["contador"] += 1
                    info_correo["ultimo_intento"] = datetime.now().isoformat()
                    info_correo["ultimo_error"] = error_critico
                    
                    # Para errores críticos, esperar más tiempo
                    delay_minutos = 120  # 2 horas
                    proximo_intento = datetime.now() + timedelta(minutes=delay_minutos)
                    info_correo["proximo_intento"] = proximo_intento.isoformat()
                
                for correo in correos_creminox:
                    correo_key = f"creminox:{correo}"
                    if correo_key not in registro["correos_fallidos"][fecha_str]:
                        registro["correos_fallidos"][fecha_str][correo_key] = {"contador": 0}
                    
                    info_correo = registro["correos_fallidos"][fecha_str][correo_key]
                    info_correo["contador"] += 1
                    info_correo["ultimo_intento"] = datetime.now().isoformat()
                    info_correo["ultimo_error"] = error_critico
                    
                    delay_minutos = 120
                    proximo_intento = datetime.now() + timedelta(minutes=delay_minutos)
                    info_correo["proximo_intento"] = proximo_intento.isoformat()
                
                for correo in correos_admin:
                    correo_key = f"admin:{correo}"
                    if correo_key not in registro["correos_fallidos"][fecha_str]:
                        registro["correos_fallidos"][fecha_str][correo_key] = {"contador": 0}
                    
                    info_correo = registro["correos_fallidos"][fecha_str][correo_key]
                    info_correo["contador"] += 1
                    info_correo["ultimo_intento"] = datetime.now().isoformat()
                    info_correo["ultimo_error"] = error_critico
                    
                    delay_minutos = 120
                    proximo_intento = datetime.now() + timedelta(minutes=delay_minutos)
                    info_correo["proximo_intento"] = proximo_intento.isoformat()
                
                set_registro(registro)
        else:
            logger.debug("✅ No hay días pendientes de envío.")

        await asyncio.sleep(120)