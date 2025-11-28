#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drive_upload.py

Utilidades para subir archivos locales a Google Drive siguiendo una estructura
de carpetas basada en un nombre “raíz” y una subcarpeta de fecha. Este módulo
reutiliza los helpers definidos en `drive_oauth.py` y expone una API sencilla
para que otros scripts (por ejemplo, `main.py`) puedan delegar todo el flujo
de autenticación, creación de carpetas, subida de archivos y generación de
enlaces compartidos.

Flujo principal:
1. Enumerar archivos en un directorio local.
2. Garantizar la existencia (o crear) una carpeta raíz en Drive.
3. Garantizar la subcarpeta para la fecha (por defecto, fecha actual).
4. Subir archivos y generar enlaces compartidos.
5. Devolver un resumen estructurado con la información relevante.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .drive_oauth import (
    build_drive_service,
    ensure_credentials,
    ensure_drive_folder,
    generate_share_link,
    upload_file_to_drive,
)

DEFAULT_LOCAL_DIR = Path(__file__).parent / "downloads"
DATE_FMT = "%Y-%m-%d"


@dataclass(frozen=True)
class DriveUploadConfig:
    """
    Parámetros que definen el comportamiento de la carga a Drive.

    Atributos:
        root_folder_name: Nombre de la carpeta “raíz” (ej. “SantaElena”).
        date_folder_name: Nombre de la subcarpeta (por defecto YYYY-MM-DD).
        parent_id: Carpeta padre donde se colocará la carpeta raíz (por defecto “root”).
        recursive: Si es True, incluye subdirectorios del directorio local.
        local_base_dir: Directorio local de origen (Path absoluto o relativo).
    """

    root_folder_name: str
    date_folder_name: Optional[str] = None
    parent_id: str = "root"
    recursive: bool = False
    local_base_dir: Path = Path(".")

    def resolved_local_dir(self) -> Path:
        """Devuelve el directorio local como Path absoluto."""
        return self.local_base_dir.expanduser().resolve()

    def resolved_date_name(self) -> str:
        """Devuelve el nombre de la carpeta de fecha (o la fecha actual)."""
        if self.date_folder_name:
            return self.date_folder_name.strip()
        return datetime.now().strftime(DATE_FMT)


@dataclass(frozen=True)
class UploadedFileSummary:
    """
    Representa el resultado de subir un archivo individual a Google Drive.

    Atributos:
        file_id: ID del archivo en Drive.
        file_name: Nombre del archivo local y en Drive (sin ruta).
        drive_path: Ruta en Drive (root/date/file).
        share_url: URL compartida generada (o None si no se pudo generar).
        mime_type: MIME type determinado por Drive.
        local_path: Ruta absoluta del archivo en el sistema local.
        local_relative_path: Ruta relativa respecto al directorio de origen.
        timestamp_context: Marca temporal de la operación (UTC).
        folder_created: True si la subcarpeta de fecha fue creada en esta ejecución.
        root_folder_created: True si la carpeta raíz fue creada en esta ejecución.
    """

    file_id: str
    file_name: str
    drive_path: str
    share_url: Optional[str]
    mime_type: Optional[str]
    local_path: str
    local_relative_path: str
    timestamp_context: str
    folder_created: bool
    root_folder_created: bool

    def as_dict(self) -> Dict[str, Any]:
        """Convierte el resumen a un diccionario serializable."""
        return {
            "id": self.file_id,
            "archivo": self.file_name,
            "ruta": self.local_relative_path,
            "ruta_destino": self.drive_path,
            "ruta_local_relativa": self.local_relative_path,
            "url_compartida": self.share_url,
            "timestamp_context": self.timestamp_context,
            "mimeType": self.mime_type,
            "local_path": self.local_path,
            "carpeta_creada": self.folder_created,
            "carpeta_raiz_creada": self.root_folder_created,
        }


def _timestamp_utc() -> str:
    """Devuelve una cadena ISO-8601 en UTC."""
    return datetime.now(timezone.utc).isoformat()


def find_local_files(directory: Path, recursive: bool = False) -> List[Path]:
    """
    Obtiene todos los archivos (no directorios) en `directory`.

    Args:
        directory: Directorio base.
        recursive: Si es True, incluye subdirectorios.

    Returns:
        Lista de rutas absolutas ordenadas alfabéticamente.

    Raises:
        FileNotFoundError: Si el directorio no existe.
    """
    dir_path = directory.expanduser().resolve()
    if not dir_path.exists():
        raise FileNotFoundError(f"El directorio local no existe: {dir_path}")

    if recursive:
        files = sorted(path for path in dir_path.rglob("*") if path.is_file())
    else:
        files = sorted(path for path in dir_path.iterdir() if path.is_file())

    return files


def upload_to_drive(
    config: DriveUploadConfig,
    files: Optional[Sequence[Path]] = None,
) -> Dict[str, Any]:
    """
    Realiza el flujo completo de subida a Drive usando la configuración indicada.

    Args:
        config: Parámetros de la operación (`DriveUploadConfig`).
        files: Lista opcional de rutas de archivos a subir. Si no se provee, se listan
               automáticamente desde `config.local_base_dir`.

    Returns:
        Un diccionario con la estructura:
        {
            "timestamp_context": ...,
            "total_archivos": int,
            "carpeta_raiz": {...},
            "carpeta_fecha": {...},
            "archivos": [UploadedFileSummary.as_dict(), ...]
        }
    """
    local_dir = config.resolved_local_dir()
    date_name = config.resolved_date_name()

    if files is None:
        files = find_local_files(local_dir, recursive=config.recursive)

    if not files:
        return {
            "timestamp_context": _timestamp_utc(),
            "total_archivos": 0,
            "error": "no_files_found",
            "mensaje": f"No se encontraron archivos en {local_dir}",
        }

    creds = ensure_credentials()
    service = build_drive_service(creds)

    root_folder = ensure_drive_folder(
        service=service,
        folder_name=config.root_folder_name,
        parent_id=config.parent_id,
        create=True,
    )
    date_folder = ensure_drive_folder(
        service=service,
        folder_name=date_name,
        parent_id=root_folder["id"],
        create=True,
    )

    summaries: List[UploadedFileSummary] = []

    for local_file in files:
        local_resolved = local_file.expanduser().resolve()
        try:
            relative_path = local_resolved.relative_to(local_dir)
        except ValueError:
            relative_path = local_resolved.name

        created_file = upload_file_to_drive(
            service=service,
            local_path=local_resolved,
            parent_id=date_folder["id"],
        )
        shared_meta = generate_share_link(
            service=service,
            file_id=created_file["id"],
            allow_file_discovery=False,
            role="reader",
        )

        summaries.append(
            UploadedFileSummary(
                file_id=shared_meta["id"],
                file_name=created_file["name"],
                drive_path=f"{config.root_folder_name}/{date_name}/{created_file['name']}",
                share_url=shared_meta.get("share_url"),
                mime_type=shared_meta.get("mimeType"),
                local_path=str(local_resolved),
                local_relative_path=str(relative_path),
                timestamp_context=_timestamp_utc(),
                folder_created=date_folder.get("created", False),
                root_folder_created=root_folder.get("created", False),
            )
        )

    result = {
        "timestamp_context": _timestamp_utc(),
        "total_archivos": len(summaries),
        "carpeta_raiz": {
            "id": root_folder["id"],
            "nombre": root_folder["name"],
            "creada": root_folder.get("created", False),
        },
        "carpeta_fecha": {
            "id": date_folder["id"],
            "nombre": date_folder["name"],
            "creada": date_folder.get("created", False),
        },
        "archivos": [summary.as_dict() for summary in summaries],
    }
    return result


def summarize_upload_to_json(summary: Dict[str, Any], indent: int = 2) -> str:
    """
    Serializa un diccionario de resumen en formato JSON con codificación UTF-8.

    Args:
        summary: Resultado devuelto por `upload_to_drive`.
        indent: Cantidad de espacios para la indentación (por defecto 2).

    Returns:
        Una cadena JSON lista para imprime o guardar en archivo.
    """
    return json.dumps(summary, ensure_ascii=False, indent=indent)


def upload_directory_to_drive(
    nombre: str,
    fecha: Optional[str] = None,
    directorio: Path | str = DEFAULT_LOCAL_DIR,
    parent_id: str = "root",
    recursivo: bool = False,
) -> Dict[str, Any]:
    """
    Interfaz de alto nivel: sube todos los archivos de `directorio` a Drive.

    Args:
        nombre: Nombre de la carpeta raíz en Drive.
        fecha: Nombre de la subcarpeta de fecha. Si es None, se usa la fecha actual.
        directorio: Directorio local con los archivos a subir.
        parent_id: ID del contenedor padre en Drive (default “root”).
        recursivo: Si es True, incluye subdirectorios del directorio local.

    Returns:
        Un diccionario con el resumen del proceso (idéntico al de `upload_to_drive`).
    """
    config = DriveUploadConfig(
        root_folder_name=nombre.strip(),
        date_folder_name=fecha.strip() if fecha else None,
        parent_id=parent_id.strip() or "root",
        recursive=recursivo,
        local_base_dir=Path(directorio),
    )
    return upload_to_drive(config=config)


__all__ = [
    "DEFAULT_LOCAL_DIR",
    "DATE_FMT",
    "DriveUploadConfig",
    "UploadedFileSummary",
    "find_local_files",
    "upload_to_drive",
    "summarize_upload_to_json",
    "upload_directory_to_drive",
]
