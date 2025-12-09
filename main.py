import datetime
import os
import shutil
import sys

import yaml

# Agregar el directorio actual al sys.path para poder importar módulos locales
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import src.google_drive as drive
from src.services.downloader import descargar_pdf
from src.services.drive_source import (
    finalizar_archivo_en_drive,
    obtener_archivo_desde_drive,
)
from src.services.excel_updater import copiar_y_actualizar_excel
from src.services.pdf_extractor import extraer_datos_registros
from src.services.reader import extraer_url_desde_xlsx, leer_archivo_xlsx
from src.services.scraper import (
    iniciar_sesion,
    navegar_a_nueva_version,
    navegar_a_ultima_pagina,
    procesar_folios,
)
from src.utils.email_mapping import cargar_plantilla
from src.utils.email_sender import enviar_correo_api


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

    # Extraer datos de los PDFs descargados
    print("\n📄 Extrayendo datos de montos desde PDFs...\n")
    extraer_datos_registros(registros)

    return registros


# Enviar informe único a destinatario configurado
def enviar_informe_unico(ruta_archivo_actualizado, config, registros):
    """
    Envía el archivo Excel actualizado a un único destinatario.
    Incluye tabla de folios que no se pudieron procesar.

    Args:
        ruta_archivo_actualizado: Ruta del archivo Excel actualizado con columnas Q-U
        config: Configuración del sistema
        registros: Lista de registros procesados para identificar fallidos

    Returns:
        bool: True si el correo se envió correctamente
    """
    print("\n📧 Preparando envío de correo con informe...")

    # Obtener destinatario desde config
    destinatario = config.get("correo", {}).get("destinatario_informe")
    cc = config.get("correo", {}).get("cc", "")

    if not destinatario:
        print("❌ No se encontró destinatario_informe en config.yaml")
        return False

    # Formato del asunto
    fecha_asunto = datetime.datetime.now().strftime("%d%m%Y")
    formato_asunto = f"({fecha_asunto}EXP)"

    # Cargar plantilla HTML
    plantilla_html = cargar_plantilla()

    if not plantilla_html:
        print("❌ No se pudo cargar la plantilla HTML. No se enviará correo.")
        return False

    # Identificar registros fallidos (sin PDF o sin subir a Drive)
    registros_fallidos = [
        r
        for r in registros
        if not getattr(r, "estado_pdf", False) or not getattr(r, "estado_subida", False)
    ]

    # Generar mensaje
    nombre_archivo = os.path.basename(ruta_archivo_actualizado)
    mensaje = f"Se adjunta el informe de facturas procesadas: <strong>{nombre_archivo}</strong>"

    # Generar tabla de folios fallidos si hay
    tabla_fallidos = ""
    if registros_fallidos:
        mensaje += f"<br><br>⚠️ <strong>{len(registros_fallidos)} folios no pudieron ser procesados completamente:</strong>"

        tabla_fallidos = """
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; margin-top: 10px;">
            <thead style="background-color: #f2f2f2;">
                <tr>
                    <th>Folio</th>
                    <th>RUT Proveedor</th>
                    <th>Razón Social</th>
                    <th>Motivo</th>
                </tr>
            </thead>
            <tbody>
        """

        for reg in registros_fallidos:
            # Determinar motivo del fallo
            if not getattr(reg, "estado_pdf", False):
                motivo = "Sin PDF descargado"
            elif not getattr(reg, "estado_subida", False):
                error = getattr(reg, "error", "") or "Error al subir"
                motivo = f"No subido: {error[:50]}"
            else:
                motivo = "Error desconocido"

            razon_social = getattr(reg, "razon_social", "")[:40]

            tabla_fallidos += f"""
                <tr>
                    <td>{reg.folio}</td>
                    <td>{reg.rut_proveedor}</td>
                    <td>{razon_social}</td>
                    <td>{motivo}</td>
                </tr>
            """

        tabla_fallidos += """
            </tbody>
        </table>
        """
    else:
        mensaje += "<br><br>✅ Todos los folios fueron procesados correctamente."

    contenido_html = plantilla_html.replace("{{VAR_MENSAJE}}", mensaje)
    contenido_html = contenido_html.replace("{{TABLA_FOLIOS_FALLIDOS}}", tabla_fallidos)

    # Enviar correo
    print(f"   📤 Enviando a: {destinatario}")
    if cc:
        print(f"   📤 CC: {cc}")

    enviado = enviar_correo_api(
        destinatarios=[destinatario],
        asunto=f"FACTURAS PARA APROBACIÓN {formato_asunto}",
        cuerpo_html=contenido_html,
        archivos_adjuntos=[ruta_archivo_actualizado],
        cc=[cc] if cc else None,
    )

    if enviado:
        print(f"✅ Correo enviado correctamente a {destinatario}")
    else:
        print(f"❌ Error al enviar correo a {destinatario}")

    return enviado


# Mover archivos procesados a carpeta Listos con fecha/hora
def mover_archivos_procesados(
    ruta_archivo_original, ruta_archivo_actualizado, carpeta_listos, fecha, hora
):
    """
    Mueve el archivo original y el actualizado a la carpeta de procesados (Listos).

    La carpeta de destino tiene estructura:
    Listos/{fecha}/{hora}/
    Ejemplo: Listos/2025-12-08/20.00.00/

    Args:
        ruta_archivo_original: Ruta del archivo original (Por Hacer/SEMANA 40.xlsx)
        ruta_archivo_actualizado: Ruta del archivo actualizado (informes/SEMANA 40_timestamp.xlsx)
        carpeta_listos: Carpeta base de procesados (desde config.yaml)
        fecha: Fecha de ejecución (formato: 2025-12-08)
        hora: Hora de ejecución (formato: 20.00.00)
    """
    print("\n📁 Moviendo archivos a carpeta de procesados (Listos)...")

    # Crear estructura: Listos/{fecha}/{hora}/
    carpeta_fecha = os.path.join(carpeta_listos, fecha)
    carpeta_destino = os.path.join(carpeta_fecha, hora)
    os.makedirs(carpeta_destino, exist_ok=True)

    print(f"   📂 Carpeta destino: {carpeta_destino}")

    # Mover archivo original
    if ruta_archivo_original and os.path.exists(ruta_archivo_original):
        try:
            nombre_original = os.path.basename(ruta_archivo_original)
            destino_original = os.path.join(carpeta_destino, nombre_original)
            shutil.move(ruta_archivo_original, destino_original)
            print(f"   ✅ Archivo original movido: {nombre_original}")
        except Exception as e:
            print(f"   ⚠️ Error al mover archivo original: {e}")

    # Mover archivo actualizado
    if ruta_archivo_actualizado and os.path.exists(ruta_archivo_actualizado):
        try:
            nombre_actualizado = os.path.basename(ruta_archivo_actualizado)
            destino_actualizado = os.path.join(carpeta_destino, nombre_actualizado)
            shutil.move(ruta_archivo_actualizado, destino_actualizado)
            print(f"   ✅ Archivo actualizado movido: {nombre_actualizado}")
        except Exception as e:
            print(f"   ⚠️ Error al mover archivo actualizado: {e}")

    print(f"📁 Archivos procesados guardados en: {carpeta_destino}")


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

    # Lista para registros sin PDF que también deben incluirse en el resultado
    registros_sin_pdf = []

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
            # Registrar el registro sin PDF para incluirlo en los resultados
            registro.estado_subida = False
            registro.drive_url = None
            registro.ruta_drive = None
            registro.tipo_archivo = None
            registro.error = "Sin PDF disponible para subir"
            registros_sin_pdf.append(registro)
            print(
                f"   ⚠ Folio {registro.folio}: Sin archivos (estado_pdf={getattr(registro, 'estado_pdf', None)})"
            )

    # Agregar Excel procesado
    if ruta_archivo_procesado and Path(ruta_archivo_procesado).exists():
        archivos_a_subir.append(Path(ruta_archivo_procesado))
        print(f"   ✓ Excel procesado: {Path(ruta_archivo_procesado).name}")

    if not archivos_a_subir:
        print("⚠️  No hay archivos para subir a Drive")
        # Aún así retornamos todos los registros (sin PDF) para que se incluyan en informes
        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "carpeta_destino": f"{ruta_drive}/{fecha_hoy}",
            "exitosos": 0,
            "fallidos": 0,
            "sin_pdf": len(registros_sin_pdf),
            "resultados": registros_sin_pdf,  # Incluir todos los registros sin PDF
        }

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

        # Combinar resultados: registros subidos + registros sin PDF
        todos_los_resultados = resultados_por_registro + registros_sin_pdf

        print(f"\n{'=' * 60}")
        print(f"📤 {exitosos}/{len(mapa_registros)} archivos subidos a Drive")
        print(f"⚠️  {len(registros_sin_pdf)} registros sin PDF (incluidos en informe)")
        print(f"📁 {ruta_drive}/{fecha_hoy}/[empresa]/archivo")
        print(f"{'=' * 60}\n")

        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "carpeta_destino": f"{ruta_drive}/{fecha_hoy}",
            "exitosos": exitosos,
            "fallidos": len(mapa_registros) - exitosos,
            "sin_pdf": len(registros_sin_pdf),
            "resultados": todos_los_resultados,  # Incluye TODOS los registros
        }

    except Exception as e:
        print(f"\n❌ Error: {e}")
        # En caso de error, aún incluimos los registros sin PDF
        return {
            "exitosos": 0,
            "fallidos": len(registros),
            "sin_pdf": len(registros_sin_pdf) if "registros_sin_pdf" in locals() else 0,
            "resultados": registros_sin_pdf if "registros_sin_pdf" in locals() else [],
            "error": str(e),
        }


# Función principal
def main():
    """
    Función principal del sistema de procesamiento de facturas.

    Flujo:
    0. Buscar y descargar archivo desde Google Drive (Por Hacer remoto)
    1. Leer Excel original de "Por Hacer" local
    2. Scraping en IConstruye
    3. Descargar PDFs y extraer montos
    4. Subir a Google Drive
    5. Copiar y actualizar Excel con columnas Q-U
    6. Enviar correo a destinatario único
    7. Mover archivos a carpeta procesados (fecha/hora)
    8. Mover archivo procesado en Drive a carpeta "Procesados"
    """
    print("\n" + "=" * 60)
    print("🚀 INICIANDO PROCESO DE FACTURAS")
    print("=" * 60 + "\n")

    # Generar fecha y hora para la ejecución
    ahora = datetime.datetime.now()
    fecha_ejecucion = ahora.strftime("%Y-%m-%d")
    hora_ejecucion = ahora.strftime("%H.%M.%S")
    timestamp = f"{fecha_ejecucion}_{hora_ejecucion}"
    print(f"⏰ Fecha: {fecha_ejecucion} | Hora: {hora_ejecucion}")

    # Cargar configuración
    config = configuracion()
    ruta_drive = config["google_drive"]["carpeta_destino"]
    directorio_informes = config.get("informes", {}).get("directorio_local")
    carpeta_listos = config.get("procesados", {}).get("carpeta_listos")

    if not carpeta_listos:
        # Fallback a carpeta por defecto si no está configurada
        carpeta_listos = (
            "/Volumes/Resources/Develop/SmartBots/Santa_Elena/Contabilidad/Listos"
        )
        print(f"⚠️ carpeta_listos no configurada, usando: {carpeta_listos}")

    if not directorio_informes:
        directorio_informes = os.path.join(os.path.dirname(__file__), "informes")

    # 0. Buscar y descargar archivo desde Google Drive
    print("\n☁️ Paso 0: Buscando archivos en Google Drive...")
    drive_service, file_id_drive, folder_id_drive, ruta_descargada = (
        obtener_archivo_desde_drive(config)
    )

    if not file_id_drive:
        print("📭 No hay archivos para procesar en Google Drive. Finalizando.")
        return

    # 1. Leer registros del archivo Excel original (ahora descargado de Drive)
    print("\n📖 Paso 1: Leyendo archivo Excel original...")
    resultado_excel = obtener_excel()
    if resultado_excel is None:
        print("❌ No se pudieron cargar registros. Finalizando.")
        return
    registros, ruta_archivo_original = resultado_excel
    print(f"   ✅ {len(registros)} registros cargados desde: {ruta_archivo_original}")

    # 2. Scraping en IConstruye
    print("\n🌐 Paso 2: Iniciando scraping en IConstruye...")
    driver = scrapping()
    if driver is None:
        print("❌ Error en scraping. Finalizando.")
        return

    # 3. Procesar folios (buscar, descargar PDFs, extraer montos)
    print("\n🔄 Paso 3: Procesando folios...")
    registros = procesamiento_excel(driver, registros)

    # 4. Subir archivos a Google Drive
    print("\n☁️ Paso 4: Subiendo archivos a Google Drive...")
    registros_con_drive = copiar_drive(registros, ruta_archivo_original, ruta_drive)

    # Validar que hay resultados para procesar
    resultados = registros_con_drive.get("resultados", [])
    if not resultados:
        print("⚠️ No hay registros para procesar después de copiar a Drive.")
        mover_archivos_procesados(
            ruta_archivo_original, None, carpeta_listos, fecha_ejecucion, hora_ejecucion
        )
        print("=== Fin del Proceso (sin registros) ===\n")
        return

    # 5. Copiar y actualizar Excel con nuevas columnas (Q-U)
    print("\n📊 Paso 5: Actualizando Excel con datos extraídos...")
    ruta_archivo_actualizado = copiar_y_actualizar_excel(
        ruta_archivo_original=ruta_archivo_original,
        registros=resultados,
        directorio_salida=directorio_informes,
        timestamp=timestamp,
    )

    # 6. Enviar correo a destinatario único
    print("\n📧 Paso 6: Enviando correo con informe...")
    enviar_informe_unico(ruta_archivo_actualizado, config, resultados)

    # 7. Mover archivos a carpeta de procesados (Listos/fecha/hora)
    print("\n📁 Paso 7: Moviendo archivos a Listos...")
    mover_archivos_procesados(
        ruta_archivo_original,
        ruta_archivo_actualizado,
        carpeta_listos,
        fecha_ejecucion,
        hora_ejecucion,
    )

    # 8. Mover archivo procesado en Drive a carpeta "Procesados"
    print("\n☁️ Paso 8: Moviendo archivo en Drive a Procesados...")
    if drive_service and file_id_drive and folder_id_drive:
        finalizar_archivo_en_drive(
            drive_service,
            file_id_drive,
            folder_id_drive,
            config,
            fecha=fecha_ejecucion,
            hora=hora_ejecucion,
        )
    else:
        print("⚠️ No se pudo mover el archivo en Drive (faltan datos de conexión)")

    print("\n" + "=" * 60)
    print("✅ PROCESO COMPLETADO EXITOSAMENTE")
    print(
        f"📁 Archivos locales en: {carpeta_listos}/{fecha_ejecucion}/{hora_ejecucion}/"
    )
    print(f"☁️ Archivo en Drive movido a: Procesados/{fecha_ejecucion}/")
    print("=" * 60 + "\n")


# Ejecutar la función principal
if __name__ == "__main__":
    main()
