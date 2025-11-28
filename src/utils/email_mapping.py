import pandas as pd
import yaml
import os

# Cargar configuración desde config.yaml usando ruta absoluta
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)




RUTA_PLANTILLA = config["web_scraping"]["plantilla_correo"]

def cargar_plantilla():
        """Carga la plantilla HTML desde la ruta especificada en `config.yaml`."""
        try:
            with open(RUTA_PLANTILLA, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            print(f"❌ Error al cargar la plantilla HTML: {e}")
            return None


from datetime import datetime

def generar_contenido_html(rut, pdfs_fallidos):
    """
    Genera el mensaje y la tabla de PDFs fallidos en formato HTML.
    
    Args:
        rut (str): RUT del proveedor.
        pdfs_fallidos (list): Lista de registros que no pudieron descargar su PDF.

    Returns:
        tuple: (var_mensaje, tabla_folios_fallidos)
    """
    var_mensaje = f"Estimado/a, adjunto los documentos descargados para el RUT {rut}."
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Construcción de la tabla con los folios fallidos
    if pdfs_fallidos:
        var_mensaje = "Junto con saludar, se adjuntan las facturas del día; además, se indica que la(s) siguiente(s) factura(s) no se encuentra(n) en IConstruye"
        tabla_folios_fallidos = """
        <table border="1" cellpadding="5" cellspacing="0">
            <tr>
                <th>Rut Proveedor</th>
                <th>Razon Social</th> 
                <th>Folio</th>
                <th>Fecha Documento</th>
            </tr>
        """
        for registro in pdfs_fallidos:
            fecha_formateada = (
                    datetime.strptime(registro.fecha_docto, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y")
                    if registro.fecha_docto else ''
                )
            tabla_folios_fallidos += f"""
            <tr>
                <td>{registro.rut_proveedor}</td>
                <td>{registro.razon_social}</td>
                <td>{registro.folio}</td>
                <td>{fecha_formateada}</td>
            </tr>
            """
        tabla_folios_fallidos += "</table>"
    else:
        var_mensaje = "Junto con saludar, se adjuntan las facturas del día."
        tabla_folios_fallidos = ""

    return var_mensaje, tabla_folios_fallidos





RUTA_EXCEL_CORREOS = config["web_scraping"]["areas_correos"]

def cargar_correos_por_area():
    """
    Carga los correos electrónicos por área desde un archivo Excel definido en `config.yaml`.

    Returns:
        dict: Diccionario con las áreas en mayúsculas como clave y listas de correos como valores.
    """
    df = pd.read_excel(RUTA_EXCEL_CORREOS, dtype=str)  # Asegurar que todo se lea como string
    correos_por_area = {}

    for _, row in df.iterrows():
        area = str(row["Area"]).strip().upper()  # Normalizar a mayúsculas
        correos = [email.strip() for email in str(row["Correos"]).split(",") if email.strip()]
        correos_por_area[area] = correos

    return correos_por_area


def asignar_correos_a_areas(agrupados_por_area):
    """
    Asigna los correos correspondientes a cada área usando el archivo Excel de configuración.

    Args:
        agrupados_por_area (dict): Diccionario con las áreas como clave y una lista de registros como valor.

    Returns:
        dict: Diccionario actualizado con los correos asignados.
    """
    correos_por_area = cargar_correos_por_area()  # Leer configuración desde Excel

    for area in agrupados_por_area.keys():
        area_normalizada = area.upper()  # Asegurar que siempre se comparen en mayúsculas
        if area_normalizada in correos_por_area:
            agrupados_por_area[area] = {
                "destinatarios": correos_por_area[area_normalizada],
                "registros": agrupados_por_area[area]
            }
        else:
            agrupados_por_area[area] = {
                "destinatarios": [],
                "registros": agrupados_por_area[area]
            }
    
    return agrupados_por_area