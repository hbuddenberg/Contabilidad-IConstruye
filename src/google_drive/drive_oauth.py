#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de autenticación, listado y descarga de archivos de Google Drive.

Características:
- Autenticación OAuth con cliente de tipo "Desktop app".
- Lista archivos en All Drives (Mi unidad + Unidades compartidas).
- Descarga por ID o por ruta dentro de "Mi unidad".
- Configuración vía YAML (download_dir, file_id, file_path).
- CLI con flags: --config, --file-id, --file-path, --download-dir, --list, --folder-path.
- Manejo de errores y logs claros.
- Resolución de accesos directos (shortcuts) al destino real.
- Verificación de capabilities.canDownload antes de descargar.

Limitaciones actuales:
- No exporta documentos nativos de Google (Docs/Sheets/Slides). Si apuntas a uno de ellos, mostrará un mensaje indicando que no está soportado en esta versión.
"""

from __future__ import annotations

import argparse
import io
import json
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Directorios y archivos
SCRIPT_DIR = Path(__file__).parent.parent
SECRETS_DIR = SCRIPT_DIR / "configuration"
CLIENT_SECRETS_FILE = SECRETS_DIR / "credentials.json"
TOKEN_FILE = SECRETS_DIR / "token.json"

# Scopes:
# - drive.readonly: leer contenido (permite descargar)
# - metadata.readonly: solo metadatos
# - drive.file: solo archivos creados/abiertos por la app (no lista todo)
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
]

# Tamaño de página para list()
PAGE_SIZE = 100


def save_token(creds: Credentials) -> None:
    """Guarda el token en disco."""
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")


def load_token(expected_scopes: List[str]) -> Optional[Credentials]:
    """Carga el token si existe y coincide con los scopes esperados."""
    if not TOKEN_FILE.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), expected_scopes)
        # Si los scopes otorgados no coinciden, forzar nuevo consentimiento
        granted = set(creds.scopes or [])
        expected = set(expected_scopes)
        if granted != expected:
            print("⚠️  Los scopes del token existente no coinciden con los esperados.")
            print(f"   Otorgados: {sorted(granted)}")
            print(f"   Esperados: {sorted(expected)}")
            print("   Se solicitará un nuevo consentimiento...")
            return None
        return creds
    except Exception as e:
        print(
            f"⚠️  No se pudo cargar el token existente ({e}). Se solicitará nuevo consentimiento."
        )
        return None


def ensure_credentials() -> Credentials:
    """Obtiene credenciales válidas, refrescando o iniciando el flujo OAuth si es necesario."""
    if not CLIENT_SECRETS_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró {CLIENT_SECRETS_FILE}. "
            "Asegúrate de colocar tu client_secrets.json en poc_googledrive/secrets/"
        )

    creds = load_token(SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        print("🔄 Credenciales expiradas. Intentando refrescar...")
        try:
            creds.refresh(Request())
            save_token(creds)
            return creds
        except Exception as e:
            error_msg = str(e)
            # Detectar error de token revocado/expirado
            if (
                "invalid_grant" in error_msg.lower()
                or "token has been expired or revoked" in error_msg.lower()
            ):
                print(f"❌ Error: {error_msg}")
                print("🗑️  Token revocado o expirado. Eliminando token.json...")
                if TOKEN_FILE.exists():
                    TOKEN_FILE.unlink()
                    print("✅ token.json eliminado. Iniciando nueva autenticación...")
                # Reintentar con flujo completo
                creds = None
            else:
                # Si es otro error, re-lanzarlo
                raise

    print("🔐 Iniciando flujo de consentimiento en el navegador...")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    save_token(creds)
    return creds


def build_drive_service(creds: Credentials):
    """Crea el cliente de Google Drive API."""
    return build("drive", "v3", credentials=creds)


def list_all_drives_files(service, page_size: int = PAGE_SIZE) -> List[Dict]:
    """Lista archivos en All Drives (Mi unidad + Unidades compartidas), sin papelera."""
    items: List[Dict] = []
    page_token: Optional[str] = None

    while True:
        response = (
            service.files()
            .list(
                pageSize=page_size,
                pageToken=page_token,
                q="trashed = false",
                fields="nextPageToken, files(id, name, mimeType, owners(displayName))",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                corpora="allDrives",
                spaces="drive",
            )
            .execute()
        )
        batch = response.get("files", [])
        items.extend(batch)
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return items


def _q(value: str) -> str:
    """Escapa comillas simples para usar en consultas 'q'."""
    return value.replace("'", "\\'")


def resolve_path_to_id(service, file_path: str) -> str:
    """
    Resuelve una ruta (en 'Mi unidad') a un fileId.
    - file_path: p. ej., "Carpeta/Subcarpeta/archivo.pdf"
    - Solo soporta rutas dentro de 'Mi unidad' (corpora='user').
      Para archivos en 'Unidades compartidas', usa 'file_id' directamente.
    """
    parts = [p for p in file_path.strip("/").split("/") if p]
    if not parts:
        raise ValueError("La ruta no puede estar vacía.")

    parent_id = "root"  # 'Mi unidad'
    # Resolver carpetas
    for folder_name in parts[:-1]:
        q = (
            f"name = '{_q(folder_name)}' "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and '{parent_id}' in parents and trashed = false"
        )
        resp = (
            service.files()
            .list(
                q=q,
                pageSize=10,
                fields="files(id, name)",
                corpora="user",
                spaces="drive",
                supportsAllDrives=True,
            )
            .execute()
        )
        folders = resp.get("files", [])
        if not folders:
            raise FileNotFoundError(
                f"No se encontró la carpeta '{folder_name}' dentro del padre {parent_id}."
            )
        # Si hay múltiples, tomar la primera (se puede mejorar con desambiguación)
        parent_id = folders[0]["id"]

    # Resolver archivo final
    file_name = parts[-1]
    q = f"name = '{_q(file_name)}' and '{parent_id}' in parents and trashed = false"
    resp = (
        service.files()
        .list(
            q=q,
            pageSize=10,
            fields="files(id, name)",
            corpora="user",
            spaces="drive",
            supportsAllDrives=True,
        )
        .execute()
    )
    files = resp.get("files", [])
    if not files:
        raise FileNotFoundError(
            f"No se encontró el archivo '{file_name}' en la ruta especificada."
        )
    if len(files) > 1:
        # Podríamos desambiguar, por ahora tomar el primero
        print(
            f"⚠️  Advertencia: se encontraron múltiples archivos llamados '{file_name}'. Se usará el primero."
        )
    return files[0]["id"]


def download_file_by_id(service, file_id: str, download_dir: Path) -> Path:
    """
    Descarga un archivo por fileId a la carpeta indicada.
    - Para archivos nativos de Google (Docs/Sheets/Slides), no se exporta en esta versión.
    - Resuelve accesos directos (shortcuts) al destino real.
    """
    meta = (
        service.files()
        .get(
            fileId=file_id,
            fields="id, name, mimeType, md5Checksum, size, owners(displayName,emailAddress), capabilities(canDownload), shortcutDetails(targetId,targetMimeType)",
            supportsAllDrives=True,
        )
        .execute()
    )
    # Resolver accesos directos (shortcuts) al destino real
    if meta.get("mimeType") == "application/vnd.google-apps.shortcut":
        shortcut = meta.get("shortcutDetails", {}) or {}
        target_id = shortcut.get("targetId")
        target_mime = shortcut.get("targetMimeType", "")
        if not target_id:
            raise FileNotFoundError(
                "El acceso directo no contiene targetId en shortcutDetails."
            )
        print(
            f"🔁 El archivo es un acceso directo. Resolviendo al destino {target_id}..."
        )
        # Reemplazar file_id por el destino y volver a obtener metadatos del archivo real
        file_id = target_id
        meta = (
            service.files()
            .get(
                fileId=file_id,
                fields="id, name, mimeType, md5Checksum, size, owners(displayName,emailAddress), capabilities(canDownload)",
                supportsAllDrives=True,
            )
            .execute()
        )

    cap = meta.get("capabilities", {}) or {}
    owners = meta.get("owners", []) or []
    can_download = cap.get("canDownload", True)
    owner_info = (
        ", ".join(
            [
                f"{o.get('displayName', 'Desconocido')} <{o.get('emailAddress', '?')}>"
                for o in owners
            ]
        )
        or "N/D"
    )
    print(f"   Propietario(s): {owner_info} • canDownload={can_download}")
    if not can_download:
        raise PermissionError(
            "El propietario ha deshabilitado la descarga de este archivo (canDownload=false)."
        )

    name = meta["name"]
    mime_type = meta.get("mimeType", "")

    if mime_type.startswith("application/vnd.google-apps."):
        raise NotImplementedError(
            f"No se descarga contenido de archivos nativos de Google ('{mime_type}') en esta versión."
        )

    download_dir.mkdir(parents=True, exist_ok=True)
    dest_path = download_dir / name

    request = service.files().get_media(
        fileId=file_id, supportsAllDrives=True, acknowledgeAbuse=True
    )
    fh = io.FileIO(dest_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        if status:
            print(f"   Progreso: {int(status.progress() * 100)}%")

    print(f"✅ Archivo descargado en: {dest_path}")
    return dest_path


def ensure_drive_folder(
    service,
    folder_name: str,
    parent_id: str = "root",
    create: bool = True,
) -> Dict[str, Any]:
    """
    Obtiene (y opcionalmente crea) una carpeta en Drive dentro del padre indicado.

    Args:
        service: Cliente autenticado de Google Drive.
        folder_name: Nombre de la carpeta a ubicar/crear.
        parent_id: ID de la carpeta padre (root por defecto).
        create: Si es True y no existe, crea la carpeta.

    Returns:
        Dict con metadatos de la carpeta (id, name, parents).

    Raises:
        FileNotFoundError: si no existe y create=False.
    """
    query = (
        f"name = '{_q(folder_name)}' "
        "and mimeType = 'application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed = false"
    )
    response = (
        service.files()
        .list(
            q=query,
            pageSize=1,
            fields="files(id, name, parents)",
            supportsAllDrives=True,
            spaces="drive",
        )
        .execute()
    )
    files = response.get("files", [])
    if files:
        existing = files[0]
        existing["created"] = False
        return existing

    if not create:
        raise FileNotFoundError(
            f"No se encontró la carpeta '{folder_name}' dentro del padre {parent_id}."
        )

    body: Dict[str, Any] = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        body["parents"] = [parent_id]

    created_folder = (
        service.files()
        .create(
            body=body,
            fields="id, name, parents",
            supportsAllDrives=True,
        )
        .execute()
    )
    created_folder["created"] = True
    return created_folder


def upload_file_to_drive(
    service,
    local_path: Path | str,
    parent_id: str,
) -> Dict[str, Any]:
    """
    Sube un archivo local a Drive y devuelve sus metadatos.

    Args:
        service: Cliente autenticado de Google Drive.
        local_path: Ruta local del archivo.
        parent_id: Carpeta destino en Drive.

    Returns:
        Dict con metadatos del archivo creado (incluye webViewLink).

    Raises:
        FileNotFoundError: si el archivo local no existe.
    """
    path_obj = Path(local_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"No se encontró el archivo local: {path_obj}")

    mime_type = mimetypes.guess_type(path_obj.name)[0] or "application/octet-stream"
    media = MediaFileUpload(
        filename=str(path_obj),
        mimetype=mime_type,
        resumable=False,
    )
    body: Dict[str, Any] = {"name": path_obj.name}
    if parent_id:
        body["parents"] = [parent_id]

    created_file = (
        service.files()
        .create(
            body=body,
            media_body=media,
            fields="id, name, mimeType, parents, webViewLink, webContentLink",
            supportsAllDrives=True,
        )
        .execute()
    )
    created_file["created"] = True
    if created_file.get("webViewLink"):
        created_file["share_url"] = created_file["webViewLink"]
    elif created_file.get("webContentLink"):
        created_file["share_url"] = created_file["webContentLink"]
    else:
        created_file["share_url"] = None
    return created_file


def generate_share_link(
    service,
    file_id: str,
    allow_file_discovery: bool = False,
    role: str = "reader",
) -> Dict[str, Any]:
    """
    Genera (o asegura) un enlace compartido para un archivo de Drive.

    Args:
        service: Cliente autenticado de Google Drive.
        file_id: ID del archivo.
        allow_file_discovery: Si True, el archivo es encontrable por búsqueda.
        role: rol asignado (p.ej., 'reader', 'commenter').

    Returns:
        Dict con metadatos del archivo (webViewLink, webContentLink, etc.).
    """
    permission = {
        "type": "anyone",
        "role": role,
        "allowFileDiscovery": allow_file_discovery,
    }
    try:
        service.permissions().create(
            fileId=file_id,
            body=permission,
            fields="id",
            supportsAllDrives=True,
            sendNotificationEmail=False,
        ).execute()
    except HttpError as e:
        # Ignora error si la permisión 'anyone' ya existe
        try:
            payload = json.loads(e.content.decode("utf-8"))
        except Exception:
            payload = {}
        reason = (payload.get("error", {}) or {}).get("errors", [{}])[0].get("reason")
        if e.resp.status != 409 and reason != "alreadyExists":
            raise

    metadata = (
        service.files()
        .get(
            fileId=file_id,
            fields="id, name, mimeType, parents, webViewLink, webContentLink, iconLink",
            supportsAllDrives=True,
        )
        .execute()
    )
    metadata["share_url"] = metadata.get("webViewLink") or metadata.get(
        "webContentLink"
    )
    metadata.setdefault("created", False)
    return metadata


def load_yaml_config(path: Path) -> Dict[str, Any]:
    """Carga configuración YAML si existe. Si no existe, devuelve dict vacío."""
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(
            "El archivo de configuración YAML no contiene un mapeo válido."
        )
    return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Listar o descargar archivos de Google Drive (My Drive + Shared Drives)."
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(SCRIPT_DIR / "config.yaml"),
        help="Ruta al archivo YAML de configuración (por defecto: ./config.yaml).",
    )
    parser.add_argument(
        "--file-id",
        type=str,
        help="ID de archivo en Google Drive a descargar (tiene prioridad sobre file_path).",
    )
    parser.add_argument(
        "--file-path",
        type=str,
        help="Ruta dentro de 'Mi unidad' (p. ej., 'Carpeta/Sub/archivo.pdf') a descargar.",
    )
    parser.add_argument(
        "--download-dir",
        type=str,
        help="Carpeta de descarga local. Si no se especifica, usa ./downloads.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Forzar modo listado (ignora parámetros de descarga si se activa).",
    )
    parser.add_argument(
        "--folder-path",
        type=str,
        help="Ruta de una carpeta en 'Mi unidad' para listar su contenido (ej: 'Proyectos/Reportes'). Si es un ID de carpeta, se usará directamente.",
    )
    args = parser.parse_args()

    # Cargar configuración YAML y fusionar con argumentos (args tiene prioridad)
    cfg_path = Path(args.config) if args.config else SCRIPT_DIR / "config.yaml"
    cfg = load_yaml_config(cfg_path)
    file_id = args.file_id or cfg.get("file_id")
    file_path = args.file_path or cfg.get("file_path")
    download_dir = Path(
        args.download_dir or cfg.get("download_dir", SCRIPT_DIR / "downloads")
    )
    folder_path = args.folder_path

    print("➡️  Preparando autenticación con Google Drive...")
    creds = ensure_credentials()
    granted_scopes = sorted(set(creds.scopes or []))
    print("✅ Autenticado correctamente.")
    print(f"   Scopes concedidos: {granted_scopes}")

    try:
        service = build_drive_service(creds)

        # Listar contenido de una carpeta específica (por ruta o por ID)
        if folder_path:
            # Intentar resolver como ruta en 'Mi unidad'; si falla, tratar como ID
            try:
                target_folder_id = resolve_path_to_id(service, folder_path)
                print(
                    f"📂 Listando contenido de la carpeta (ruta resuelta): {folder_path}"
                )
            except Exception:
                # Tratar como ID directo (soporta Unidades compartidas)
                target_folder_id = folder_path
                print(f"📂 Listando contenido de la carpeta (ID): {folder_path}")
            try:
                meta = (
                    service.files()
                    .get(
                        fileId=target_folder_id,
                        fields="id, name, mimeType",
                        supportsAllDrives=True,
                    )
                    .execute()
                )
                if meta.get("mimeType") != "application/vnd.google-apps.folder":
                    raise ValueError(
                        "El ID/ruta proporcionado no corresponde a una carpeta."
                    )
                print(f"   Nombre de la carpeta: {meta['name']}")
            except Exception as e:
                print(f"❌ No se pudo acceder a la carpeta: {e}")
                return

            q = f"'{target_folder_id}' in parents and trashed = false"
            try:
                response = (
                    service.files()
                    .list(
                        q=q,
                        pageSize=PAGE_SIZE,
                        fields="nextPageToken, files(id, name, mimeType, owners(displayName))",
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                        spaces="drive",
                    )
                    .execute()
                )
                items = response.get("files", [])
                if not items:
                    print(
                        "ℹ️  La carpeta está vacía o no tienes permisos para ver su contenido."
                    )
                else:
                    print(f"✅ Archivos en la carpeta: {len(items)}")
                    for item in items:
                        owner = (
                            item.get("owners", [{}])[0].get("displayName")
                            if item.get("owners")
                            else "Desconocido"
                        )
                        print(
                            f"- {item.get('name')} ({item.get('id')}) • {item.get('mimeType')} • Owner: {owner}"
                        )
                return
            except HttpError as e:
                print(f"❌ Error al listar la carpeta: {e}")
                return

        # Flujo por defecto: descargar usando config/CLI; si no hay parámetros válidos, error claro
        if not args.list:
            if file_id or file_path:
                if file_id:
                    target_id = file_id
                    print(f"📥 Descargando por file_id: {target_id}")
                else:
                    print(f"🔎 Resolviendo ruta en 'Mi unidad': {file_path}")
                    target_id = resolve_path_to_id(service, file_path)
                    print(f"📌 file_id resuelto: {target_id}")
                download_file_by_id(service, target_id, download_dir)
                return
            else:
                print("❗ No se especificó 'file_id' ni 'file_path'.")
                print(f"   Archivo de configuración usado: {cfg_path}")
                print(
                    "   Define 'file_id' o 'file_path' en config.yaml o pásalos por CLI."
                )
                print("   Ejemplos:")
                print("     uv run drive_oauth.py --file-id <ID>")
                print(
                    "     uv run drive_oauth.py --file-path 'Carpeta/Sub/archivo.pdf'"
                )
                print("   Para listar archivos usa: --list")
                print(
                    "   Para listar una carpeta específica usa: --folder-path 'Carpeta/Sub'"
                )
                return

        # Modo listado explícito
        print(
            "📂 Consultando archivos (All Drives: My Drive + Shared Drives), sin papelera..."
        )
        files = list_all_drives_files(service, page_size=PAGE_SIZE)

        if not files:
            print("ℹ️  No se encontraron archivos.")
            print("   Posibles causas:")
            print(
                "   - El scope 'drive.readonly' está correcto, pero tal vez el Drive esté vacío o sin acceso."
            )
            print(
                "   - Si esperas ver archivos de unidades compartidas, verifica tus permisos en esas unidades."
            )
            return

        print(f"✅ Archivos encontrados: {len(files)}")
        for item in files[:200]:
            owner = (
                item.get("owners", [{}])[0].get("displayName")
                if item.get("owners")
                else "Desconocido"
            )
            print(
                f"- {item.get('name')} ({item.get('id')}) • {item.get('mimeType')} • Owner: {owner}"
            )
        if len(files) > 200:
            print(f"… y {len(files) - 200} más.")

    except HttpError as e:
        # Parseo básico del error para logs más claros
        status = getattr(e, "status_code", None) or getattr(
            e.resp, "status", "desconocido"
        )
        try:
            details = json.loads(e.content.decode("utf-8"))
        except Exception:
            details = {"error": str(e)}
        print("❌ Error de la API de Google Drive")
        print(f"   HTTP Status: {status}")
        print(f"   Detalles: {json.dumps(details, indent=2, ensure_ascii=False)}")
        print("   Sugerencias:")
        print(
            "   - Verifica que la Google Drive API esté habilitada en el proyecto del client_secrets.json."
        )
        print(
            "   - Si el mensaje menciona 'accessNotConfigured', habilita la API y espera unos minutos."
        )
        print(
            "   - Si aparece 'access_denied' por app en pruebas, añade tu correo como Test user en la pantalla de consentimiento."
        )
        # Ayuda específica: detectar errores comunes y dar recomendaciones accionables
        try:
            reason = (
                (details.get("error", {}) or {}).get("errors", [{}])[0].get("reason")
            )
        except Exception:
            reason = None
        if reason == "appNotAuthorizedToFile":
            print(
                "   - Detalle: 'appNotAuthorizedToFile'. Posibles causas y soluciones:"
            )
            print(
                "     • El consentimiento previo pudo haberse hecho con 'drive.file'. Borra token.json y vuelve a autenticar para conceder 'drive.readonly'."
            )
            print(
                "     • Si el archivo era un acceso directo, ya resolvemos al destino; asegúrate de tener permisos sobre el archivo real (p. ej., en Unidad compartida)."
            )
            print(
                "     • Si es un entorno Workspace, verifica que el administrador no bloquee apps no verificadas para Drive."
            )
    except NotImplementedError as e:
        print(f"⚠️  {e}")
        print(
            "   Sugerencia: descarga por ID de archivo no nativo o implementa export para Docs/Sheets/Slides."
        )
    except Exception as e:
        print(f"❌ Error inesperado: {e}")


if __name__ == "__main__":
    main()
