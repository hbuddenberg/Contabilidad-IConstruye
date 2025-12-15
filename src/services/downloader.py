import datetime
import os
import time

import requests
import yaml

# Cargar configuración desde config.yaml usando ruta absoluta
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

CARPETA_DESCARGAS = config["web_scraping"][
    "carpeta_descargas"
]  # Ruta base de descargas


def descargar_pdf(registros):
    """
    Recorre las instancias de la clase, usa `url_archivo` para descargar un PDF
    y lo guarda en la subcarpeta 'Facturas PDF' dentro de la carpeta del día.
    Actualiza `ruta_pdf` y `estado_pdf` en la instancia.
    """
    fecha_hoy = datetime.datetime.now().strftime("%Y-%m-%d")
    carpeta_facturas = os.path.join(CARPETA_DESCARGAS, fecha_hoy, "Facturas PDF")
    os.makedirs(carpeta_facturas, exist_ok=True)  # Crear carpeta si no existe

    for registro in registros:
        if not registro.url_archivo:  # Si no hay URL, marcar como fallo
            registro.estado_pdf = False
            registro.ruta_pdf = None
            print(f"⚠️ No hay URL para descargar PDF en el folio {registro.folio}.")
            continue

        try:
            response = requests.get(
                registro.url_archivo, timeout=10
            )  # Hacer la solicitud con un timeout de 10s
            if response.status_code == 200:
                # Guardar el archivo con el nombre basado en el Folio y RUT
                rut_limpio = registro.rut_proveedor.replace(".", "")
                nombre_pdf = f"{registro.folio}+{rut_limpio}.pdf"
                ruta_pdf = os.path.join(carpeta_facturas, nombre_pdf)

                with open(ruta_pdf, "wb") as file:
                    file.write(response.content)

                registro.ruta_pdf = ruta_pdf
                registro.estado_pdf = True
                print(f"✅ PDF descargado correctamente: {ruta_pdf}")
            else:
                registro.estado_pdf = False
                registro.ruta_pdf = None
                print(
                    f"❌ No se pudo descargar PDF para folio {registro.folio}, código HTTP: {response.status_code}"
                )

        except requests.exceptions.RequestException as e:
            registro.estado_pdf = False
            registro.ruta_pdf = None
            print(f"⚠️ Error en la descarga del PDF para folio {registro.folio}: {e}")

        time.sleep(3)
