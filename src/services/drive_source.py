"""
Módulo para obtener archivos desde Google Drive.

Este módulo proporciona funcionalidades para:
- Listar archivos en una carpeta de Google Drive
- Descargar archivos de Drive a una carpeta local
- Mover archivos procesados a otra carpeta en Drive
- Limpiar carpetas locales antes de procesar

Autor: Sistema de Contabilidad IConstruye
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import src.google_drive as drive


def limpiar_carpeta_local(carpeta: str) -> bool:
    """
    Limpia todos los archivos de una carpeta local.
    Solo elimina archivos, no subcarpetas.

    Args:
        carpeta: Ruta de la carpeta a limpiar

    Returns:
        True si se limpió correctamente, False si hubo error
    """
    try:
        carpeta_path = Path(carpeta)

        if not carpeta_path.exists():
            print(f"📁 La carpeta no existe, se creará: {carpeta}")
            carpeta_path.mkdir(parents=True, exist_ok=True)
            return True

        archivos_eliminados = 0
        for archivo in carpeta_path.iterdir():
            if archivo.is_file():
                try:
                    archivo.unlink()
                    archivos_eliminados += 1
                    print(f"   🗑️ Eliminado: {archivo.name}")
                except Exception as e:
                    print(f"   ⚠️ No se pudo eliminar {archivo.name}: {e}")

        if archivos_eliminados > 0:
            print(f"✅ Carpeta limpiada: {archivos_eliminados} archivo(s) eliminado(s)")
        else:
            print(f"📁 La carpeta ya estaba vacía: {carpeta}")

        return True

    except Exception as e:
        print(f"❌ Error al limpiar carpeta: {e}")
        return False


def limpiar_carpetas_trabajo(config: dict) -> bool:
    """
    Limpia todas las carpetas de trabajo locales antes de iniciar el proceso.
    Carpetas a limpiar:
    - Por Hacer (destino de descarga desde Drive)
    - Descargas (archivos descargados del scraping)
    - informes (reportes generados)

    Args:
        config: Diccionario de configuración con las rutas

    Returns:
        True si se limpiaron todas correctamente
    """
    print("\n🧹 Limpiando carpetas de trabajo locales...")

    carpetas_a_limpiar = []

    # Carpeta Por Hacer (destino local desde Drive)
    por_hacer = config.get("google_drive_source", {}).get("destino_local")
    if not por_hacer:
        por_hacer = config.get("ruta_archivos")
    if por_hacer:
        carpetas_a_limpiar.append(("Por Hacer", por_hacer))

    # Carpeta Descargas (del scraping)
    descargas = config.get("web_scraping", {}).get("carpeta_descargas")
    if descargas:
        carpetas_a_limpiar.append(("Descargas", descargas))

    # Carpeta informes
    informes = config.get("informes", {}).get("directorio_local")
    if informes:
        carpetas_a_limpiar.append(("Informes", informes))

    todas_ok = True
    for nombre, ruta in carpetas_a_limpiar:
        print(f"\n📁 Limpiando {nombre}: {ruta}")
        if not limpiar_carpeta_local(ruta):
            todas_ok = False

    if todas_ok:
        print("\n✅ Todas las carpetas de trabajo han sido limpiadas")
    else:
        print("\n⚠️ Algunas carpetas no pudieron ser limpiadas completamente")

    return todas_ok


def listar_archivos_por_hacer(service, ruta_drive: str) -> list:
    """
    Lista archivos Excel en la carpeta de Google Drive especificada.

    Args:
        service: Servicio de Google Drive autenticado
        ruta_drive: Ruta en Drive (ej: "SantaElena/IConstruye/Por Hacer")

    Returns:
        Lista de diccionarios con {id, name, mimeType} ordenados por nombre
    """
    try:
        # Resolver la ruta a un folder_id
        folder_id = _resolver_carpeta_id(service, ruta_drive)

        if not folder_id:
            print(f"⚠️ No se encontró la carpeta: {ruta_drive}")
            return []

        # Buscar archivos Excel en la carpeta
        query = (
            f"'{folder_id}' in parents "
            f"and trashed = false "
            f"and (mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' "
            f"or mimeType = 'application/vnd.ms-excel' "
            f"or name contains '.xlsx' "
            f"or name contains '.xls')"
        )

        response = (
            service.files()
            .list(
                q=query,
                pageSize=100,
                fields="files(id, name, mimeType, createdTime, modifiedTime)",
                orderBy="name",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )

        archivos = response.get("files", [])

        if archivos:
            print(f"📂 Se encontraron {len(archivos)} archivo(s) en Drive:")
            for archivo in archivos:
                print(f"   - {archivo['name']}")
        else:
            print(f"📭 No hay archivos Excel en: {ruta_drive}")

        return archivos

    except Exception as e:
        print(f"❌ Error al listar archivos en Drive: {e}")
        return []


def descargar_archivo_de_drive(
    service, file_id: str, file_name: str, destino_local: str
) -> Optional[str]:
    """
    Descarga un archivo de Drive a la carpeta local especificada.

    Args:
        service: Servicio de Google Drive autenticado
        file_id: ID del archivo en Drive
        file_name: Nombre del archivo
        destino_local: Ruta de la carpeta local destino

    Returns:
        Ruta completa del archivo descargado, o None si falla
    """
    try:
        # Asegurar que la carpeta destino existe
        destino_path = Path(destino_local)
        destino_path.mkdir(parents=True, exist_ok=True)

        # Verificar si ya existe un archivo con el mismo nombre
        ruta_destino = destino_path / file_name
        if ruta_destino.exists():
            print(f"⚠️ Ya existe un archivo con el nombre: {file_name}")
            # Agregar timestamp para evitar sobrescribir
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_base = ruta_destino.stem
            extension = ruta_destino.suffix
            file_name = f"{nombre_base}_{timestamp}{extension}"
            ruta_destino = destino_path / file_name
            print(f"   Se renombrará a: {file_name}")

        print(f"📥 Descargando '{file_name}' desde Google Drive...")

        # Usar la función existente de drive_oauth
        ruta_descargada = drive.download_file_by_id(service, file_id, destino_path)

        print(f"✅ Archivo descargado en: {ruta_descargada}")
        return str(ruta_descargada)

    except Exception as e:
        print(f"❌ Error al descargar archivo de Drive: {e}")
        return None


def mover_archivo_procesado_drive(
    service,
    file_id: str,
    carpeta_origen_id: str,
    carpeta_destino: str,
    fecha: str = None,
    hora: str = None,
) -> bool:
    """
    Mueve un archivo en Drive de una carpeta a otra (de "Por Hacer" a "Procesados").
    Organiza por fecha y hora: Procesados/YYYY-MM-DD/HH.MM.SS/archivo.xlsx

    Args:
        service: Servicio de Google Drive autenticado
        file_id: ID del archivo a mover
        carpeta_origen_id: ID de la carpeta origen (Por Hacer)
        carpeta_destino: Ruta destino en Drive (ej: "SantaElena/IConstruye/Procesados")
        fecha: Fecha de ejecución (formato: YYYY-MM-DD). Si es None, usa fecha actual.
        hora: Hora de ejecución (formato: HH.MM.SS). Si es None, usa hora actual.

    Returns:
        True si se movió correctamente, False en caso contrario
    """
    try:
        # Obtener fecha y hora para organizar
        if not fecha:
            fecha = datetime.now().strftime("%Y-%m-%d")
        if not hora:
            hora = datetime.now().strftime("%H.%M.%S")

        # Resolver o crear la carpeta destino base
        destino_id = _resolver_o_crear_carpeta(service, carpeta_destino)

        if not destino_id:
            print(f"❌ No se pudo resolver/crear la carpeta: {carpeta_destino}")
            return False

        # Crear subcarpeta con fecha
        carpeta_fecha = drive.ensure_drive_folder(
            service, fecha, destino_id, create=True
        )
        carpeta_fecha_id = carpeta_fecha["id"]

        # Crear subcarpeta con hora dentro de la fecha
        carpeta_hora = drive.ensure_drive_folder(
            service, hora, carpeta_fecha_id, create=True
        )
        carpeta_hora_id = carpeta_hora["id"]

        # Mover el archivo: quitar del padre anterior, agregar al nuevo
        service.files().update(
            fileId=file_id,
            addParents=carpeta_hora_id,
            removeParents=carpeta_origen_id,
            supportsAllDrives=True,
            fields="id, parents",
        ).execute()

        print(f"✅ Archivo movido a: {carpeta_destino}/{fecha}/{hora}/")
        return True

    except Exception as e:
        print(f"❌ Error al mover archivo en Drive: {e}")
        return False


def obtener_archivos_desde_drive(config: dict) -> tuple:
    """
    Función que busca y lista TODOS los archivos desde Google Drive.
    Limpia las carpetas locales antes de iniciar.

    Args:
        config: Diccionario de configuración con las rutas de Drive

    Returns:
        tuple: (service, archivos_lista, folder_id, destino_local) o (None, [], None, None) si no hay archivos
               archivos_lista es una lista de dicts con {id, name, mimeType}
    """
    try:
        # Obtener configuración de Drive
        drive_source = config.get("google_drive_source", {})
        ruta_por_hacer = drive_source.get(
            "carpeta_por_hacer", "SantaElena/IConstruye/Por Hacer"
        )
        destino_local = drive_source.get(
            "destino_local", config.get("ruta_archivos", "")
        )

        if not destino_local:
            print("❌ No se configuró el destino local para archivos")
            return None, [], None, None

        print(f"\n☁️ Conectando con Google Drive...")
        print(f"   📂 Carpeta origen: {ruta_por_hacer}")
        print(f"   📁 Destino local: {destino_local}")

        # Autenticar con Drive
        creds = drive.ensure_credentials()
        service = drive.build_drive_service(creds)

        # Listar archivos disponibles
        archivos = listar_archivos_por_hacer(service, ruta_por_hacer)

        if not archivos:
            print("📭 No hay archivos para procesar en Google Drive")
            return None, [], None, None

        print(f"\n📋 Se encontraron {len(archivos)} archivo(s) para procesar")

        # Obtener el ID de la carpeta origen para poder mover después
        folder_id = _resolver_carpeta_id(service, ruta_por_hacer)

        return service, archivos, folder_id, destino_local

    except Exception as e:
        print(f"❌ Error al obtener archivos desde Drive: {e}")
        return None, [], None, None


def descargar_un_archivo_de_drive(
    service, archivo: dict, destino_local: str, config: dict
) -> Optional[str]:
    """
    Descarga UN archivo de Drive a la carpeta local.
    Limpia las carpetas de trabajo antes de descargar.

    Args:
        service: Servicio de Google Drive autenticado
        archivo: Dict con {id, name} del archivo
        destino_local: Ruta de la carpeta local destino
        config: Configuración para limpiar carpetas

    Returns:
        Ruta del archivo descargado o None si falla
    """
    try:
        file_id = archivo["id"]
        file_name = archivo["name"]

        print(f"\n📥 Descargando: {file_name}")

        # Limpiar todas las carpetas de trabajo antes de descargar
        limpiar_carpetas_trabajo(config)

        # Descargar a carpeta local
        ruta_descargada = descargar_archivo_de_drive(
            service, file_id, file_name, destino_local
        )

        if not ruta_descargada:
            print(f"❌ Error al descargar el archivo: {file_name}")
            return None

        return ruta_descargada

    except Exception as e:
        print(f"❌ Error al descargar archivo: {e}")
        return None


def obtener_archivo_desde_drive(config: dict) -> tuple:
    """
    Función de compatibilidad que obtiene UN archivo desde Google Drive.
    Mantiene la firma anterior para compatibilidad.

    Args:
        config: Diccionario de configuración con las rutas de Drive

    Returns:
        tuple: (service, file_id, folder_id, ruta_local) o (None, None, None, None) si no hay archivos
    """
    service, archivos, folder_id, destino_local = obtener_archivos_desde_drive(config)

    if not archivos:
        return None, None, None, None

    # Limpiar carpetas y descargar el primer archivo
    limpiar_carpetas_trabajo(config)

    archivo = archivos[0]
    ruta_descargada = descargar_archivo_de_drive(
        service, archivo["id"], archivo["name"], destino_local
    )

    if not ruta_descargada:
        return None, None, None, None

    return service, archivo["id"], folder_id, ruta_descargada


def finalizar_archivo_en_drive(
    service,
    file_id: str,
    folder_id: str,
    config: dict,
    fecha: str = None,
    hora: str = None,
    ruta_archivo_actualizado: Optional[str] = None,
) -> bool:
    """
    Mueve el archivo original a Procesados y sube el archivo actualizado.
    Organiza en subcarpetas por fecha y hora.

    Args:
        service: Servicio de Google Drive autenticado
        file_id: ID del archivo original procesado
        folder_id: ID de la carpeta origen (Por Hacer)
        config: Diccionario de configuración
        fecha: Fecha de ejecución (formato: YYYY-MM-DD)
        hora: Hora de ejecución (formato: HH.MM.SS)
        ruta_archivo_actualizado: Ruta local del archivo Excel actualizado para subir

    Returns:
        True si se completó correctamente
    """
    try:
        drive_source = config.get("google_drive_source", {})
        carpeta_procesados = drive_source.get(
            "carpeta_procesados", "SantaElena/IConstruye/Procesados"
        )

        print(f"\n☁️ Moviendo archivo original en Drive a Procesados...")
        print(f"   📂 Destino: {carpeta_procesados}/{fecha}/{hora}/")

        # Mover archivo original
        resultado = mover_archivo_procesado_drive(
            service, file_id, folder_id, carpeta_procesados, fecha, hora
        )

        # Subir archivo actualizado a la misma carpeta
        if ruta_archivo_actualizado and Path(ruta_archivo_actualizado).exists():
            print(f"\n📤 Subiendo archivo actualizado a Procesados...")

            # Obtener fecha y hora
            if not fecha:
                fecha = datetime.now().strftime("%Y-%m-%d")
            if not hora:
                hora = datetime.now().strftime("%H.%M.%S")

            # Resolver o crear la carpeta destino: Procesados/fecha/hora
            destino_id = _resolver_o_crear_carpeta(service, carpeta_procesados)
            carpeta_fecha = drive.ensure_drive_folder(
                service, fecha, destino_id, create=True
            )
            carpeta_hora = drive.ensure_drive_folder(
                service, hora, carpeta_fecha["id"], create=True
            )

            # Subir archivo actualizado
            archivo_subido = drive.upload_file_to_drive(
                service, Path(ruta_archivo_actualizado), carpeta_hora["id"]
            )

            print(
                f"   ✅ Archivo actualizado subido: {Path(ruta_archivo_actualizado).name}"
            )

        return resultado

    except Exception as e:
        print(f"❌ Error al finalizar archivo en Drive: {e}")
        return False


def _resolver_carpeta_id(service, ruta_drive: str) -> Optional[str]:
    """
    Resuelve una ruta de carpeta en Drive a su ID.

    Args:
        service: Servicio de Google Drive
        ruta_drive: Ruta de la carpeta (ej: "SantaElena/IConstruye/Por Hacer")

    Returns:
        ID de la carpeta o None si no existe
    """
    try:
        partes = [p for p in ruta_drive.strip("/").split("/") if p]

        if not partes:
            return "root"

        parent_id = "root"

        for carpeta_nombre in partes:
            # Escapar comillas simples
            nombre_escapado = carpeta_nombre.replace("'", "\\'")

            query = (
                f"name = '{nombre_escapado}' "
                f"and mimeType = 'application/vnd.google-apps.folder' "
                f"and '{parent_id}' in parents "
                f"and trashed = false"
            )

            response = (
                service.files()
                .list(
                    q=query,
                    pageSize=10,
                    fields="files(id, name)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )

            carpetas = response.get("files", [])

            if not carpetas:
                print(f"⚠️ No se encontró la carpeta: {carpeta_nombre}")
                return None

            parent_id = carpetas[0]["id"]

        return parent_id

    except Exception as e:
        print(f"❌ Error al resolver carpeta: {e}")
        return None


def _resolver_o_crear_carpeta(service, ruta_drive: str) -> Optional[str]:
    """
    Resuelve una ruta de carpeta en Drive, creándola si no existe.

    Args:
        service: Servicio de Google Drive
        ruta_drive: Ruta de la carpeta (ej: "SantaElena/IConstruye/Procesados")

    Returns:
        ID de la carpeta
    """
    try:
        partes = [p for p in ruta_drive.strip("/").split("/") if p]

        if not partes:
            return "root"

        parent_id = "root"

        for carpeta_nombre in partes:
            carpeta = drive.ensure_drive_folder(
                service, carpeta_nombre, parent_id, create=True
            )
            parent_id = carpeta["id"]

        return parent_id

    except Exception as e:
        print(f"❌ Error al resolver/crear carpeta: {e}")
        return None
