#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI liviano para subir archivos desde un directorio local a Google Drive.

Delegamos toda la lógica compleja al módulo `drive_upload`, que se encarga de:
1. Autenticarse con Drive (vía `drive_oauth`).
2. Crear/ubicar la carpeta raíz y la subcarpeta de fecha en Drive.
3. Subir los archivos locales seleccionados.
4. Generar enlaces compartidos y producir un resumen estructurado.

Este script únicamente:
- Parsea argumentos CLI.
- Construye la configuración adecuada.
- Ejecuta la subida.
- Imprime o guarda el resultado en JSON.

Ejemplo de uso:
    uv run python main.py --nombre "SantaElena" --directorio ./downloads
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import drive_upload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sube archivos desde un directorio local a Google Drive dentro de una "
            "carpeta raíz y una subcarpeta con fecha."
        )
    )
    parser.add_argument(
        "--nombre",
        required=True,
        help="Nombre de la carpeta raíz en Drive (ej. 'SantaElena').",
    )
    parser.add_argument(
        "--fecha",
        default=None,
        help=(
            "Nombre de la subcarpeta (formato YYYY-MM-DD). "
            "Si no se especifica, se usa la fecha actual."
        ),
    )
    parser.add_argument(
        "--directorio",
        type=Path,
        default=drive_upload.DEFAULT_LOCAL_DIR,
        help=(
            "Directorio local con archivos a subir. "
            f"Por defecto: {drive_upload.DEFAULT_LOCAL_DIR}"
        ),
    )
    parser.add_argument(
        "--parent-id",
        default="root",
        help="ID de la carpeta padre en Drive donde se ubicará la carpeta raíz.",
    )
    parser.add_argument(
        "--recursivo",
        action="store_true",
        help="Si se indica, se incluyen archivos de subdirectorios.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Archivo donde guardar el resumen en JSON. Si no se indica, se imprime.",
    )
    return parser.parse_args()


def run_upload(
    nombre: str,
    fecha: Optional[str],
    directorio: Path,
    parent_id: str,
    recursivo: bool,
) -> dict:
    """
    Ejecuta la subida de archivos usando `drive_upload.upload_directory_to_drive`.
    """
    return drive_upload.upload_directory_to_drive(
        nombre=nombre,
        fecha=fecha,
        directorio=directorio,
        parent_id=parent_id,
        recursivo=recursivo,
    )


def main() -> None:
    args = parse_args()

    summary = run_upload(
        nombre=args.nombre.strip(),
        fecha=args.fecha.strip() if args.fecha else None,
        directorio=args.directorio,
        parent_id=args.parent_id.strip() or "root",
        recursivo=args.recursivo,
    )

    output_json = drive_upload.summarize_upload_to_json(summary)

    if args.output:
        args.output.write_text(output_json, encoding="utf-8")
        print(f"Resumen guardado en {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
