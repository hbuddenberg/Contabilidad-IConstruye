#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Paquete google_drive - Utilidades para interactuar con Google Drive.

Este paquete proporciona funcionalidades para:
- Autenticación OAuth con Google Drive
- Listado y descarga de archivos
- Creación de carpetas y subida de archivos
- Generación de enlaces compartidos

Módulos:
    - drive_oauth: Autenticación y operaciones básicas de Drive
    - drive_upload: Subida de archivos con estructura de carpetas
    - main: CLI para subir directorios completos

Ejemplos de uso:

    # Autenticación y servicio
    from google_drive import ensure_credentials, build_drive_service

    creds = ensure_credentials()
    service = build_drive_service(creds)

    # Subir archivos a Drive
    from google_drive import upload_directory_to_drive

    resultado = upload_directory_to_drive(
        nombre="SantaElena",
        fecha="2025-11-27",
        directorio="./downloads"
    )

    # Descargar archivos
    from google_drive import download_file_by_id
    from pathlib import Path

    download_file_by_id(service, "file_id_123", Path("./downloads"))

    # Crear carpetas y subir archivos individuales
    from google_drive import ensure_drive_folder, upload_file_to_drive

    carpeta = ensure_drive_folder(service, "MiCarpeta", parent_id="root")
    archivo = upload_file_to_drive(service, "./documento.pdf", carpeta["id"])
"""

from __future__ import annotations

# Importar funciones principales de drive_oauth
from .drive_oauth import (
    SCOPES,
    build_drive_service,
    download_file_by_id,
    ensure_credentials,
    ensure_drive_folder,
    generate_share_link,
    list_all_drives_files,
    load_token,
    load_yaml_config,
    move_file_in_drive,
    resolve_path_to_id,
    save_token,
    upload_file_to_drive,
)

# Importar funciones y clases de drive_upload
from .drive_upload import (
    DATE_FMT,
    DEFAULT_LOCAL_DIR,
    DriveUploadConfig,
    UploadedFileSummary,
    find_local_files,
    summarize_upload_to_json,
    upload_directory_to_drive,
    upload_to_drive,
)

__version__ = "0.1.0"

__all__ = [
    # Constantes
    "SCOPES",
    "DATE_FMT",
    "DEFAULT_LOCAL_DIR",
    # Clases
    "DriveUploadConfig",
    "UploadedFileSummary",
    # Autenticación
    "ensure_credentials",
    "build_drive_service",
    "save_token",
    "load_token",
    # Operaciones de Drive
    "list_all_drives_files",
    "resolve_path_to_id",
    "download_file_by_id",
    "ensure_drive_folder",
    "upload_file_to_drive",
    "move_file_in_drive",
    "generate_share_link",
    # Operaciones de alto nivel
    "find_local_files",
    "upload_to_drive",
    "upload_directory_to_drive",
    "summarize_upload_to_json",
    # Utilidades
    "load_yaml_config",
]
