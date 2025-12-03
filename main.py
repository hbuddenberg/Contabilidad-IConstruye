import datetime
import os
import shutil
import sys

import yaml

# Agregar el directorio actual al sys.path para poder importar módulos locales
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import src.google_drive as drive
from src.services.downloader import descargar_pdf
from src.services.reader import extraer_url_desde_xlsx, leer_archivo_xlsx
from src.services.scraper import (
    iniciar_sesion,
    navegar_a_nueva_version,
    navegar_a_ultima_pagina,
    procesar_folios,
)
from src.utils.email_mapping import (
    asignar_correos_a_areas,
    cargar_plantilla,
    generar_contenido_html,
)
from src.utils.email_sender import enviar_correo_api
from src.utils.grouping import agrupar_por_area


# Cargar configuración para obtener carpeta de descargas usando ruta absoluta
def configuracion():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return config


# Leer registros del archivo Excel
def obtener_excel():
    registros, ruta_archivo_procesado = leer_archivo_xlsx()
    if not registros:
        print("⚠️ No se pudieron cargar registros. Deteniendo ejecución.")
        return

    print(f"✅ {len(registros)} registros cargados correctamente.")
    for registro in registros[:5]:  # Mostrar solo los primeros 5 registros
        print(registro)

    return registros, ruta_archivo_procesado


# Iniciar sesión y Navegar a las dos URLs
def scrapping():
    # Iniciar sesión
    driver = iniciar_sesion()
    if not driver:
        print("❌ No se pudo autenticar después de 2 intentos.")
        return

    print("✅ Inicio de sesión completado y validado.")

    # Navegar a las dos URLs
    if not (navegar_a_nueva_version(driver) and navegar_a_ultima_pagina(driver)):
        print("❌ No se pudo ingresar.")
        return

    return driver


# Procesar folios (buscar y actualizar estado)
def procesamiento_excel(driver, registros):
    # Procesar folios (buscar y actualizar estado)
    procesar_folios(driver, registros)

    print(registros)

    # Extraer URL desde los archivos descargados
    print("\n🔍 Extrayendo URLs desde archivos descargados...\n")
    extraer_url_desde_xlsx(registros)
    descargar_pdf(registros)

    driver.quit()
    return registros


# Generar informe por Area agrupada
def generar_informe_area(agrupados_por_area):
    return none


# Asignar correos y enviar correos
def asignacion_correo(registros):
    agrupados_por_area = agrupar_por_area(registros)
    agrupados_por_area = agrupados_por_area(agrupados_por_area)

    asignar_correos_a_areas(agrupados_por_area)
    # cc = ["ltarrillo@santaelena.com"]
    cc = ["h.buddenberg@gmail.com"]
    # Obtener la fecha actual en formato ddmmyyyy
    fecha_asunto = datetime.datetime.now().strftime("%d%m%Y")

    # Crear la variable con el formato (ddmmyyyyEXP)
    formato_asunto = f"({fecha_asunto}EXP)"

    plantilla_html = cargar_plantilla()

    for rut, data in agrupados_por_area.items():
        destinatarios = data["destinatarios"]
        registros = data["registros"]

        if not destinatarios:
            print(f"⚠️ No se enviará correo. No hay destinatarios para {rut}.")
            continue

        archivos_adjuntos = [
            registro.ruta_pdf for registro in registros if registro.estado_pdf
        ]
        pdfs_fallidos = [registro for registro in registros if not registro.estado_pdf]

        var_mensaje, tabla_folios_fallidos = generar_contenido_html(rut, pdfs_fallidos)

        contenido_html = plantilla_html.replace("{{VAR_MENSAJE}}", var_mensaje)
        contenido_html = contenido_html.replace(
            "{{TABLA_FOLIOS_FALLIDOS}}", tabla_folios_fallidos
        )

        enviado = enviar_correo_api(
            destinatarios=destinatarios,
            asunto=f"FACTURAS PARA APROBACIÓN {formato_asunto}",
            cuerpo_html=contenido_html,
            archivos_adjuntos=archivos_adjuntos,
            cc=cc,
        )

    print(f"✅ Correo {'enviado' if enviado else 'NO enviado'} a {destinatarios}.")


# Mover el archivo procesado a la carpeta de descargas con fecha
def mover_procesados(ruta_archivo_procesado, config):
    # Mover el archivo procesado a la carpeta de descargas con fecha
    if ruta_archivo_procesado:
        try:
            fecha_hoy = datetime.datetime.now().strftime("%Y-%m-%d")
            carpeta_descargas = config["web_scraping"]["carpeta_descargas"]
            carpeta_con_fecha = os.path.join(carpeta_descargas, fecha_hoy)
            os.makedirs(carpeta_con_fecha, exist_ok=True)

            # Nombre del archivo original
            nombre_archivo = os.path.basename(ruta_archivo_procesado)
            destino_archivo = os.path.join(carpeta_con_fecha, nombre_archivo)

            # Mover el archivo
            shutil.move(ruta_archivo_procesado, destino_archivo)
            print(f"✅ Archivo procesado movido a: {destino_archivo}")
        except Exception as e:
            print(f"⚠️ Error al mover el archivo procesado: {e}")


# Subir archivos a Google Drive
def copiar_drive(registros, ruta_archivo_procesado, ruta_drive):
    """
    Sube archivos de registros a Google Drive organizados por fecha.

    Args:
        registros: Lista de objetos Registro con archivos descargados
        ruta_archivo_procesado: Ruta del archivo Excel procesado
        ruta_drive: Ruta base en Drive (ej: "SantaElena/IConstruye/Facturas")

    Returns:
        dict: Resumen con resultados de subida por registro
    """
    from pathlib import Path

    print("\n📤 Iniciando subida de archivos a Google Drive...")

    fecha_hoy = datetime.datetime.now().strftime("%Y-%m-%d")
    archivos_a_subir = []
    mapa_registros = {}  # Mapeo: nombre_archivo -> registro

    # Recopilar archivos de cada registro
    print(f"📋 Recopilando archivos de {len(registros)} registros...")

    for registro in registros:
        # Determinar qué archivo subir (prioridad: PDF, Excel, CSV, texto plano)
        archivo_path = None
        tipo = None

        if (
            hasattr(registro, "ruta_pdf")
            and registro.ruta_pdf
            and Path(registro.ruta_pdf).exists()
        ):
            archivo_path = Path(registro.ruta_pdf)
            tipo = "PDF"
        elif (
            hasattr(registro, "ruta_archivo")
            and registro.ruta_archivo
            and Path(registro.ruta_archivo).exists()
        ):
            archivo_path = Path(registro.ruta_archivo)
            # Determinar tipo por extensión
            ext = archivo_path.suffix.lower()
            if ext in [".xlsx", ".xls"]:
                tipo = "Excel"
            elif ext == ".csv":
                tipo = "CSV"
            elif ext in [".txt", ".log"]:
                tipo = "Texto"
            else:
                tipo = "Archivo"

        if archivo_path and tipo == "PDF":
            archivos_a_subir.append(archivo_path)
            mapa_registros[archivo_path.name] = {
                "registro": registro,
                "tipo": tipo,
                "path": archivo_path,
            }
            print(f"   ✓ Folio {registro.folio}: {tipo} ({archivo_path.name})")
        else:
            print(f"   ⚠ Folio {registro.folio}: Sin archivos")

    # Agregar Excel procesado
    if ruta_archivo_procesado and Path(ruta_archivo_procesado).exists():
        archivos_a_subir.append(Path(ruta_archivo_procesado))
        print(f"   ✓ Excel procesado: {Path(ruta_archivo_procesado).name}")

    if not archivos_a_subir:
        print("⚠️  No hay archivos para subir")
        return {"exitosos": 0, "fallidos": len(registros)}

    try:
        print(f"\n🚀 Subiendo {len(archivos_a_subir)} archivos...")

        # Autenticar una sola vez
        creds = drive.ensure_credentials()
        service = drive.build_drive_service(creds)

        # Crear estructura base: ruta_drive/fecha
        partes_ruta = ruta_drive.split("/")
        parent_id = "root"
        for carpeta in partes_ruta:
            folder = drive.ensure_drive_folder(service, carpeta, parent_id, create=True)
            parent_id = folder["id"]

        carpeta_fecha = drive.ensure_drive_folder(
            service, fecha_hoy, parent_id, create=True
        )
        carpeta_fecha_id = carpeta_fecha["id"]

        # Subir cada archivo en su carpeta de empresa
        resultados_por_registro = []
        exitosos = 0

        for nombre_archivo, info in mapa_registros.items():
            reg = info["registro"]
            archivo_path = info["path"]

            # Sanitizar nombre de empresa
            nombre_empresa = "".join(
                c
                for c in reg.razon_social.strip()
                if c.isalnum() or c in (" ", "-", "_")
            ).strip()

            try:
                # Crear carpeta empresa y subir archivo
                carpeta_empresa = drive.ensure_drive_folder(
                    service, nombre_empresa, carpeta_fecha_id, create=True
                )

                archivo_subido = drive.upload_file_to_drive(
                    service, archivo_path, carpeta_empresa["id"]
                )

                metadata = drive.generate_share_link(
                    service,
                    archivo_subido["id"],
                    allow_file_discovery=False,
                    role="reader",
                )

                # Actualizar campos del registro
                reg.tipo_archivo = info["tipo"]
                reg.estado_subida = True
                reg.drive_url = metadata.get("share_url")
                reg.ruta_drive = (
                    f"{ruta_drive}/{fecha_hoy}/{nombre_empresa}/{archivo_path.name}"
                )
                reg.error = None

                resultados_por_registro.append(reg)
                exitosos += 1
                print(
                    f"   ✓ {reg.razon_social[:40]}: {info['tipo']} - {metadata.get('share_url')}"
                )

            except Exception as e:
                # Actualizar campos del registro en caso de error
                reg.tipo_archivo = info["tipo"]
                reg.estado_subida = False
                reg.drive_url = None
                reg.ruta_drive = None
                reg.error = str(e)

                resultados_por_registro.append(reg)
                print(f"   ✗ {reg.razon_social[:40]}: {str(e)[:40]}")

        print(f"\n{'=' * 60}")
        print(f"📤 {exitosos}/{len(mapa_registros)} archivos subidos")
        print(f"📁 {ruta_drive}/{fecha_hoy}/[empresa]/archivo")
        print(f"{'=' * 60}\n")

        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "carpeta_destino": f"{ruta_drive}/{fecha_hoy}",
            "exitosos": exitosos,
            "fallidos": len(mapa_registros) - exitosos,
            "resultados": resultados_por_registro,
        }

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {"exitosos": 0, "fallidos": len(registros), "error": str(e)}


# Función principal
def main():
    # Cargar configuración para obtener carpeta de descargas usando ruta absoluta
    config = configuracion()
    ruta_drive = config["google_drive"]["carpeta_destino"]

    # Leer registros del archivo Excel
    registros, ruta_archivo_procesado = obtener_excel()

    # Iniciar sesión y Navegar a las dos URLs
    driver = scrapping()

    # Procesar folios (buscar y actualizar estado)
    registros = procesamiento_excel(driver, registros)

    # Subir archivos a Google Drive

    registros = copiar_drive(registros, ruta_archivo_procesado, ruta_drive)

    # Asignar correos y enviar correos
    asignacion_correo(registros["resultados"])

    # Mover el archivo procesado a la carpeta de descargas con fecha
    mover_procesados(ruta_archivo_procesado, config)

    print("\n✅ Todo el proceso se ejecutó correctamente.")
    print("=== Fin del Proceso ===\n")


# Ejecutar la función principal
if __name__ == "__main__":
    main()
