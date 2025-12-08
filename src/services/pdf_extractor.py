#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_extractor.py

Módulo para extraer información de montos desde archivos PDF de facturas chilenas (DTE).
Extrae: Monto Neto, Monto IVA, Monto Total.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pdfplumber

    PDF_LIBRARY = "pdfplumber"
except ImportError:
    try:
        import PyPDF2

        PDF_LIBRARY = "PyPDF2"
    except ImportError:
        PDF_LIBRARY = None


def extraer_texto_pdf(ruta_pdf: str) -> Optional[str]:
    """
    Extrae todo el texto de un archivo PDF.

    Args:
        ruta_pdf: Ruta al archivo PDF

    Returns:
        Texto extraído del PDF o None si hay error
    """
    if not os.path.exists(ruta_pdf):
        print(f"❌ Archivo no existe: {ruta_pdf}")
        return None

    if PDF_LIBRARY == "pdfplumber":
        return _extraer_con_pdfplumber(ruta_pdf)
    elif PDF_LIBRARY == "PyPDF2":
        return _extraer_con_pypdf2(ruta_pdf)
    else:
        print(
            "❌ No se encontró librería para leer PDFs. Instala: pip install pdfplumber"
        )
        return None


def _extraer_con_pdfplumber(ruta_pdf: str) -> Optional[str]:
    """Extrae texto usando pdfplumber (mejor para tablas)."""
    try:
        texto_completo = []
        with pdfplumber.open(ruta_pdf) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_completo.append(texto)
        return "\n".join(texto_completo)
    except Exception as e:
        print(f"❌ Error extrayendo texto con pdfplumber: {e}")
        return None


def _extraer_con_pypdf2(ruta_pdf: str) -> Optional[str]:
    """Extrae texto usando PyPDF2 (alternativa)."""
    try:
        texto_completo = []
        with open(ruta_pdf, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for pagina in reader.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_completo.append(texto)
        return "\n".join(texto_completo)
    except Exception as e:
        print(f"❌ Error extrayendo texto con PyPDF2: {e}")
        return None


def limpiar_monto(monto_str: str) -> Optional[int]:
    """
    Convierte un string de monto chileno a entero.

    Ejemplos:
        "$ 1.234.567" -> 1234567
        "$1.234.567" -> 1234567
        "1.234.567" -> 1234567
        "1234567" -> 1234567
    """
    if not monto_str:
        return None

    # Remover símbolos y espacios
    limpio = monto_str.replace("$", "").replace(" ", "").strip()

    # Remover puntos de miles (formato chileno)
    limpio = limpio.replace(".", "")

    # Si hay coma decimal, tomar solo la parte entera
    if "," in limpio:
        limpio = limpio.split(",")[0]

    try:
        return int(limpio)
    except ValueError:
        return None


def extraer_montos(texto: str) -> Dict[str, Optional[int]]:
    """
    Extrae montos de una factura chilena desde el texto.

    Busca patrones como:
        - MONTO NETO $ 1.234.567
        - NETO $1.234.567
        - IVA 19% $ 234.568
        - MONTO IVA $234.568
        - TOTAL $ 1.469.135
        - MONTO TOTAL $1.469.135

    Args:
        texto: Texto extraído del PDF

    Returns:
        Diccionario con monto_neto, monto_iva, monto_total
    """
    resultado: Dict[str, Optional[int]] = {
        "monto_neto": None,
        "monto_iva": None,
        "monto_total": None,
    }

    if not texto:
        return resultado

    # Normalizar texto: mayúsculas y espacios múltiples
    texto_norm = texto.upper()
    texto_norm = re.sub(r"\s+", " ", texto_norm)

    # Patrón para montos chilenos: $ seguido de números con puntos
    # Captura: $1.234.567 o $ 1.234.567 o 1.234.567
    patron_monto = r"\$?\s*([\d\.]+(?:,\d+)?)"

    # === MONTO NETO ===
    patrones_neto = [
        r"MONTO\s*NETO\s*:?\s*" + patron_monto,
        r"NETO\s*:?\s*" + patron_monto,
        r"SUB\s*TOTAL\s*NETO\s*:?\s*" + patron_monto,
        r"VALOR\s*NETO\s*:?\s*" + patron_monto,
    ]

    for patron in patrones_neto:
        match = re.search(patron, texto_norm)
        if match:
            resultado["monto_neto"] = limpiar_monto(match.group(1))
            if resultado["monto_neto"]:
                break

    # === MONTO IVA ===
    patrones_iva = [
        r"MONTO\s*IVA\s*:?\s*" + patron_monto,
        r"IVA\s*(?:\(?\s*19\s*%?\s*\)?)?\s*:?\s*" + patron_monto,
        r"I\.?V\.?A\.?\s*(?:\(?\s*19\s*%?\s*\)?)?\s*:?\s*" + patron_monto,
        r"IMPUESTO\s*:?\s*" + patron_monto,
    ]

    for patron in patrones_iva:
        match = re.search(patron, texto_norm)
        if match:
            resultado["monto_iva"] = limpiar_monto(match.group(1))
            if resultado["monto_iva"]:
                break

    # === MONTO TOTAL ===
    patrones_total = [
        r"MONTO\s*TOTAL\s*:?\s*" + patron_monto,
        r"TOTAL\s*(?:A\s*PAGAR)?\s*:?\s*" + patron_monto,
        r"VALOR\s*TOTAL\s*:?\s*" + patron_monto,
        r"TOTAL\s*FACTURA\s*:?\s*" + patron_monto,
    ]

    for patron in patrones_total:
        match = re.search(patron, texto_norm)
        if match:
            resultado["monto_total"] = limpiar_monto(match.group(1))
            if resultado["monto_total"]:
                break

    # Validación cruzada: si tenemos neto e IVA pero no total, calcularlo
    if (
        resultado["monto_neto"]
        and resultado["monto_iva"]
        and not resultado["monto_total"]
    ):
        resultado["monto_total"] = resultado["monto_neto"] + resultado["monto_iva"]

    # Si tenemos total e IVA pero no neto, calcularlo
    if (
        resultado["monto_total"]
        and resultado["monto_iva"]
        and not resultado["monto_neto"]
    ):
        resultado["monto_neto"] = resultado["monto_total"] - resultado["monto_iva"]

    return resultado


def procesar_pdf_factura(ruta_pdf: str) -> Dict[str, Any]:
    """
    Procesa un PDF de factura y extrae los montos.

    Args:
        ruta_pdf: Ruta al archivo PDF

    Returns:
        Diccionario con:
            - exito: bool
            - monto_neto: int o None
            - monto_iva: int o None
            - monto_total: int o None
            - error: str o None
            - texto_extraido: str (para debug)
    """
    resultado = {
        "exito": False,
        "monto_neto": None,
        "monto_iva": None,
        "monto_total": None,
        "error": None,
        "texto_extraido": None,
    }

    # Extraer texto del PDF
    texto = extraer_texto_pdf(ruta_pdf)

    if not texto:
        resultado["error"] = "No se pudo extraer texto del PDF"
        return resultado

    resultado["texto_extraido"] = texto[:500]  # Guardar muestra para debug

    # Extraer montos
    montos = extraer_montos(texto)

    resultado["monto_neto"] = montos["monto_neto"]
    resultado["monto_iva"] = montos["monto_iva"]
    resultado["monto_total"] = montos["monto_total"]

    # Determinar éxito: al menos el total debe estar presente
    if montos["monto_total"] is not None:
        resultado["exito"] = True
    elif montos["monto_neto"] is not None or montos["monto_iva"] is not None:
        resultado["exito"] = True  # Parcialmente exitoso
    else:
        resultado["error"] = "No se encontraron montos en el PDF"

    return resultado


def extraer_datos_registros(registros: List[Any]) -> List[Any]:
    """
    Extrae datos de PDFs para una lista de registros.
    Actualiza los campos monto_neto, monto_iva, monto_total, estado_extraccion_pdf.

    Args:
        registros: Lista de objetos Registro con ruta_pdf definida

    Returns:
        La misma lista de registros con campos actualizados
    """
    print("\n📄 Iniciando extracción de datos desde PDFs...")

    exitosos = 0
    fallidos = 0
    sin_pdf = 0

    for registro in registros:
        # Verificar si tiene PDF
        if not hasattr(registro, "ruta_pdf") or not registro.ruta_pdf:
            registro.estado_extraccion_pdf = False
            registro.error_extraccion = "Sin PDF disponible"
            sin_pdf += 1
            print(f"   ⚠ Folio {registro.folio}: Sin PDF")
            continue

        if not os.path.exists(registro.ruta_pdf):
            registro.estado_extraccion_pdf = False
            registro.error_extraccion = f"PDF no existe: {registro.ruta_pdf}"
            fallidos += 1
            print(f"   ❌ Folio {registro.folio}: PDF no encontrado")
            continue

        # Procesar PDF
        resultado = procesar_pdf_factura(registro.ruta_pdf)

        if resultado["exito"]:
            registro.estado_extraccion_pdf = True
            registro.monto_neto = resultado["monto_neto"]
            registro.monto_iva = resultado["monto_iva"]
            registro.monto_total = resultado["monto_total"]
            registro.error_extraccion = None
            exitosos += 1

            # Formatear montos para mostrar
            neto = (
                f"${resultado['monto_neto']:,}".replace(",", ".")
                if resultado["monto_neto"]
                else "N/A"
            )
            iva = (
                f"${resultado['monto_iva']:,}".replace(",", ".")
                if resultado["monto_iva"]
                else "N/A"
            )
            total = (
                f"${resultado['monto_total']:,}".replace(",", ".")
                if resultado["monto_total"]
                else "N/A"
            )

            print(
                f"   ✓ Folio {registro.folio}: Neto={neto} | IVA={iva} | Total={total}"
            )
        else:
            registro.estado_extraccion_pdf = False
            registro.error_extraccion = resultado["error"]
            fallidos += 1
            print(f"   ❌ Folio {registro.folio}: {resultado['error']}")

    print(f"\n{'=' * 60}")
    print(f"📄 Extracción completada:")
    print(f"   ✓ Exitosos: {exitosos}")
    print(f"   ❌ Fallidos: {fallidos}")
    print(f"   ⚠ Sin PDF: {sin_pdf}")
    print(f"{'=' * 60}\n")

    return registros


def extraer_datos_directorio(directorio_pdf: str) -> List[Dict[str, Any]]:
    """
    Extrae datos de todos los PDFs en un directorio.
    Útil para procesar PDFs sin tener objetos Registro.

    Args:
        directorio_pdf: Ruta al directorio con PDFs

    Returns:
        Lista de diccionarios con datos extraídos de cada PDF
    """
    resultados = []
    directorio = Path(directorio_pdf)

    if not directorio.exists():
        print(f"❌ Directorio no existe: {directorio_pdf}")
        return resultados

    pdfs = list(directorio.glob("*.pdf"))
    print(f"\n📄 Procesando {len(pdfs)} PDFs en {directorio_pdf}...")

    for pdf_path in pdfs:
        resultado = procesar_pdf_factura(str(pdf_path))
        resultado["archivo"] = pdf_path.name
        resultado["ruta"] = str(pdf_path)
        resultados.append(resultado)

        if resultado["exito"]:
            neto = (
                f"${resultado['monto_neto']:,}".replace(",", ".")
                if resultado["monto_neto"]
                else "N/A"
            )
            total = (
                f"${resultado['monto_total']:,}".replace(",", ".")
                if resultado["monto_total"]
                else "N/A"
            )
            print(f"   ✓ {pdf_path.name}: Neto={neto} | Total={total}")
        else:
            print(f"   ❌ {pdf_path.name}: {resultado['error']}")

    return resultados


# Para pruebas directas
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Procesar archivo o directorio pasado como argumento
        ruta = sys.argv[1]
        if os.path.isfile(ruta):
            resultado = procesar_pdf_factura(ruta)
            print(f"\nResultado para {ruta}:")
            print(f"  Éxito: {resultado['exito']}")
            print(f"  Monto Neto: {resultado['monto_neto']}")
            print(f"  Monto IVA: {resultado['monto_iva']}")
            print(f"  Monto Total: {resultado['monto_total']}")
            if resultado["error"]:
                print(f"  Error: {resultado['error']}")
        elif os.path.isdir(ruta):
            resultados = extraer_datos_directorio(ruta)
            print(f"\nProcesados {len(resultados)} archivos")

    else:
        print("Uso: python pdf_extractor.py <archivo.pdf|directorio>")
