#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_pdf_extractor.py

Script de prueba para extraer datos de PDFs de facturas.
Procesa todos los PDFs en el directorio de descargas y muestra los resultados.
"""

import os
import sys
from pathlib import Path

# Agregar ruta del proyecto al path de Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.pdf_extractor import extraer_datos_directorio, procesar_pdf_factura


def prueba_directorio():
    """Prueba la extracción de datos de todos los PDFs en el directorio."""
    # Ruta relativa desde este script
    ruta_pdfs = "../Descargas/2025-12-05/Facturas PDF"

    # Obtener ruta absoluta
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ruta_pdfs_completa = os.path.join(script_dir, ruta_pdfs)

    print("=" * 70)
    print("PRUEBA DE EXTRACCIÓN DE DATOS DESDE PDFs")
    print("=" * 70)
    print(f"📁 Directorio: {ruta_pdfs_completa}")
    print()

    # Verificar si el directorio existe
    if not os.path.exists(ruta_pdfs_completa):
        print(f"❌ Error: El directorio no existe")
        print(f"   Buscar en: {ruta_pdfs_completa}")
        return

    # Extraer datos de todos los PDFs
    resultados = extraer_datos_directorio(ruta_pdfs_completa)

    if not resultados:
        print("\n⚠️  No se encontraron PDFs o no se pudieron procesar")
        return

    # Mostrar resumen detallado
    print("\n" + "=" * 70)
    print("RESUMEN DETALLADO DE EXTRACCIÓN")
    print("=" * 70)

    exitosos = sum(1 for r in resultados if r["exito"])
    fallidos = len(resultados) - exitosos

    print(f"\n📊 Estadísticas:")
    print(f"   Total de PDFs: {len(resultados)}")
    print(f"   ✓ Exitosos: {exitosos}")
    print(f"   ❌ Fallidos: {fallidos}")
    print(f"   Tasa de éxito: {(exitosos / len(resultados) * 100):.1f}%")

    print(f"\n{'Archivo':<55} | {'Neto':>15} | {'IVA':>15} | {'Total':>15}")
    print("-" * 70)

    total_general = 0

    for r in resultados:
        status = "✓" if r["exito"] else "❌"
        nombre = r["archivo"][:50]

        # Formatear montos
        neto = f"${r['monto_neto']:,}".replace(",", ".") if r["monto_neto"] else "-"
        iva = f"${r['monto_iva']:,}".replace(",", ".") if r["monto_iva"] else "-"
        total = f"${r['monto_total']:,}".replace(",", ".") if r["monto_total"] else "-"

        print(f"{status} {nombre:<50} | {neto:>15} | {iva:>15} | {total:>15}")

        if r["monto_total"]:
            total_general += r["monto_total"]

    print("-" * 70)
    print(
        f"{'TOTAL GENERAL':<55} | {'':<15} | {'':<15} | ${total_general:,}".replace(
            ",", "."
        )
    )
    print("=" * 70)

    # Mostrar errores si hay
    errores = [r for r in resultados if not r["exito"] and r.get("error")]
    if errores:
        print("\n⚠️  Errores encontrados:")
        for r in errores:
            print(f"   - {r['archivo']}: {r['error']}")


def prueba_archivo_individual(ruta_archivo):
    """Prueba la extracción de un archivo PDF específico."""
    print("=" * 70)
    print("PRUEBA DE EXTRACCIÓN - ARCHIVO INDIVIDUAL")
    print("=" * 70)
    print(f"📄 Archivo: {ruta_archivo}")
    print()

    if not os.path.exists(ruta_archivo):
        print(f"❌ Error: El archivo no existe")
        return

    resultado = procesar_pdf_factura(ruta_archivo)

    print(f"Resultado:")
    print(f"  ✓ Éxito: {resultado['exito']}")
    print(
        f"  💰 Monto Neto: ${resultado['monto_neto']:,}".replace(",", ".")
        if resultado["monto_neto"]
        else "  💰 Monto Neto: N/A"
    )
    print(
        f"  📊 Monto IVA: ${resultado['monto_iva']:,}".replace(",", ".")
        if resultado["monto_iva"]
        else "  📊 Monto IVA: N/A"
    )
    print(
        f"  💵 Monto Total: ${resultado['monto_total']:,}".replace(",", ".")
        if resultado["monto_total"]
        else "  💵 Monto Total: N/A"
    )

    if resultado["error"]:
        print(f"  ❌ Error: {resultado['error']}")

    if resultado["texto_extraido"]:
        print(f"\n📝 Muestra de texto extraído:")
        print("-" * 70)
        print(resultado["texto_extraido"][:300] + "...")
        print("-" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Si se pasa un argumento, procesar ese archivo específico
        archivo = sys.argv[1]
        prueba_archivo_individual(archivo)
    else:
        # Si no hay argumentos, procesar todo el directorio
        prueba_directorio()

    print("\n✅ Prueba completada\n")
