import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import yaml

# === Configuración global ===
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file) or {}

RUTA_PLANTILLA = config.get("web_scraping", {}).get("plantilla_correo", "")
RUTA_EXCEL_CORREOS = config.get("web_scraping", {}).get("areas_correos", "")


# === Utilidades internas ===
def cargar_plantilla() -> Optional[str]:
    """
    Devuelve el HTML base del correo desde la ruta configurada.
    """
    if not RUTA_PLANTILLA:
        print("⚠️  No se definió 'plantilla_correo' en config.yaml.")
        return None

    try:
        with open(RUTA_PLANTILLA, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"❌ Error al cargar la plantilla HTML: {e}")
        return None


def formatear_fecha_tabla(valor_raw: Union[str, None]) -> str:
    """
    Intenta parsear fechas provenientes de distintas fuentes y devuelve dd-mm-YYYY.
    Si no coincide con ningún formato conocido, regresa el valor original.
    """
    valor_normalizado = str(valor_raw).strip() if valor_raw is not None else ""
    if not valor_normalizado:
        return ""

    formatos = ["%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]
    for formato in formatos:
        try:
            fecha = datetime.strptime(valor_normalizado, formato)
            return fecha.strftime("%d-%m-%Y")
        except ValueError:
            continue

    return valor_normalizado


def generar_contenido_html(rut: str, pdfs_fallidos: List) -> Tuple[str, str]:
    """
    Construye el mensaje y la tabla HTML para los folios sin PDF.
    """
    var_mensaje = f"Estimado/a, adjunto los documentos descargados para el RUT {rut}."
    if pdfs_fallidos:
        var_mensaje = (
            "Junto con saludar, se adjuntan las facturas del día; además, "
            "se indica que la(s) siguiente(s) factura(s) no se encuentra(n) "
            "en IConstruye"
        )
        tabla = [
            '<table border="1" cellpadding="5" cellspacing="0">',
            "    <tr>",
            "        <th>Rut Proveedor</th>",
            "        <th>Razon Social</th>",
            "        <th>Folio</th>",
            "        <th>Fecha Documento</th>",
            "    </tr>",
        ]
        for registro in pdfs_fallidos:
            tabla.append("    <tr>")
            tabla.append(f"        <td>{registro.rut_proveedor}</td>")
            tabla.append(f"        <td>{registro.razon_social}</td>")
            tabla.append(f"        <td>{registro.folio}</td>")
            tabla.append(
                f"        <td>{formatear_fecha_tabla(registro.fecha_docto)}</td>"
            )
            tabla.append("    </tr>")
        tabla.append("</table>")
        return var_mensaje, "\n".join(tabla)

    return "Junto con saludar, se adjuntan las facturas del día.", ""


def cargar_correos_por_area() -> Dict[str, List[str]]:
    """
    Carga y normaliza los correos configurados por área desde Excel.
    """
    if not RUTA_EXCEL_CORREOS:
        print("⚠️  No se definió 'areas_correos' en config.yaml.")
        return {}

    try:
        df = pd.read_excel(RUTA_EXCEL_CORREOS, dtype=str)
    except Exception as e:
        print(f"❌ Error al cargar el Excel de correos por área: {e}")
        return {}

    correos_por_area: Dict[str, List[str]] = {}
    for _, row in df.iterrows():
        area = str(row.get("Area", "")).strip().upper()
        correos = [
            email.strip()
            for email in str(row.get("Correos", "")).split(",")
            if email.strip()
        ]
        if area:
            correos_por_area[area] = correos

    return correos_por_area


def asignar_correos_a_areas(
    agrupados_por_area: Dict[str, Union[List, Dict]],
) -> Dict[str, Dict]:
    """
    Inyecta la lista de correos correspondientes a cada área,
    preservando metadatos previamente adjuntos (p. ej., ruta del informe).
    """
    correos_por_area = cargar_correos_por_area()

    for area, datos_area in list(agrupados_por_area.items()):
        if isinstance(datos_area, dict):
            estructura = datos_area
            registros = datos_area.get("registros", [])
        else:
            estructura = {}
            registros = datos_area

        estructura["registros"] = registros
        estructura["destinatarios"] = correos_por_area.get(area.upper(), [])
        agrupados_por_area[area] = estructura

    return agrupados_por_area
