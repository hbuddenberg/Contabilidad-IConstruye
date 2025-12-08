import base64
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Ruta de la carpeta de configuración
# CONFIG_PATH = 'C:\\Users\\junio\\OneDrive\\Documentos\\Contabilidad\\Contabilidad\\Contabilidad IConstruye\\src\\configuration'
CONFIG_PATH = Path(__file__).parent.parent / "configuration"


def autenticar():
    """
    Autentica al usuario con OAuth 2.0 y devuelve las credenciales.
    """
    creds = None
    token_path = os.path.join(CONFIG_PATH, "token.json")
    credentials_path = os.path.join(CONFIG_PATH, "credentials.json")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                error_msg = str(e)
                # Detectar error de token revocado/expirado
                if (
                    "invalid_grant" in error_msg.lower()
                    or "token has been expired or revoked" in error_msg.lower()
                ):
                    print(f"❌ Error: {error_msg}")
                    print("🗑️  Token revocado o expirado. Eliminando token.json...")
                    if os.path.exists(token_path):
                        os.remove(token_path)
                        print(
                            "✅ token.json eliminado. Iniciando nueva autenticación..."
                        )
                    # Forzar nuevo flujo de autenticación
                    creds = None
                else:
                    # Si es otro error, re-lanzarlo
                    raise

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            auth_url, _ = flow.authorization_url(
                access_type="offline", prompt="consent"
            )
            print(f"Visita esta URL para autorizar la aplicación: {auth_url}")
            creds = flow.run_local_server(port=8781)

        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    return creds


def enviar_correo_api(
    destinatarios, asunto, cuerpo_html, archivos_adjuntos=None, cc=None
):
    """
    Envía un correo utilizando la API de Gmail con OAuth 2.0.

    Args:
        destinatarios (list): Lista de destinatarios del correo.
        asunto (str): Asunto del correo.
        cuerpo_html (str): Contenido HTML del correo.
        archivos_adjuntos (list): Lista de rutas de archivos adjuntos.
        cc (list): Lista de destinatarios en copia.

    Returns:
        bool: True si el correo se envió correctamente, False en caso contrario.
    """
    creds = autenticar()
    try:
        service = build("gmail", "v1", credentials=creds)
        message = MIMEMultipart()

        # Validación y asignación de destinatarios
        if destinatarios and isinstance(destinatarios, list):
            message["To"] = ", ".join(destinatarios)
        else:
            raise ValueError(
                "No se especificaron destinatarios o el formato es inválido."
            )

        # Validación y asignación de CC
        if cc and isinstance(cc, list):
            cc_limpio = [correo.strip() for correo in cc if correo.strip()]
            if cc_limpio:
                message["Cc"] = ", ".join(cc_limpio)
        message["Subject"] = asunto
        message.attach(MIMEText(cuerpo_html, "html"))

        # Adjuntar archivos
        if archivos_adjuntos:
            for archivo in archivos_adjuntos:
                # Normalizar la ruta del archivo
                archivo_normalizado = str(archivo).replace("\\", "/")

                # Verificar si el archivo existe
                if not os.path.isfile(archivo_normalizado):
                    raise ValueError(f"Archivo no encontrado: {archivo_normalizado}")

                # Abrir y adjuntar el archivo al mensaje
                with open(archivo_normalizado, "rb") as adjunto:
                    mime_base = MIMEBase("application", "octet-stream")
                    mime_base.set_payload(adjunto.read())
                    encoders.encode_base64(mime_base)

                    # Codificar el nombre del archivo para evitar problemas con caracteres especiales
                    from email.header import Header

                    nombre_archivo = Header(
                        os.path.basename(archivo_normalizado), "utf-8"
                    ).encode()

                    # Agregar encabezado de Content-Disposition con el nombre del archivo codificado
                    mime_base.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{nombre_archivo}"',
                    )
                    message.attach(mime_base)

        # Construir y enviar el mensaje
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_message = {"raw": raw_message}

        service.users().messages().send(userId="me", body=send_message).execute()
        print("Correo enviado correctamente.")
        return True

    except HttpError as error:
        print(f"Un error ocurrió: {error}")
        return False
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
        return False
