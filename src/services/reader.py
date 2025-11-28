import os

import pandas as pd
import yaml

from src.models.registro import Registro

# Cargar configuración desde config.yaml usando ruta absoluta
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

RUTA_BASE = config.get("ruta_archivos", "")


def leer_archivo_xlsx():
    """
    Busca el archivo XLSX en la carpeta definida en config.yaml y lo procesa.
    Convierte cada fila en una instancia de Registro.

    Returns:
        tuple: (lista_registros, ruta_archivo) o ([], None) si hay error
    """
    try:
        if not os.path.exists(RUTA_BASE):
            print(f"⚠️ La ruta especificada en config.yaml no existe: {RUTA_BASE}")
            return [], None

        # Buscar archivos XLSX en la ruta
        archivos_xlsx = [f for f in os.listdir(RUTA_BASE) if f.endswith(".xlsx")]

        if not archivos_xlsx:
            print("⚠️ No se encontraron archivos XLSX en la carpeta.")
            return [], None

        # Tomamos el primer archivo encontrado
        archivo_xlsx = os.path.join(RUTA_BASE, archivos_xlsx[0])

        # Leer el archivo XLSX con pandas
        df = pd.read_excel(archivo_xlsx, dtype=str)
        print(df)

        # Verificamos si las columnas esperadas están en el archivo
        columnas_esperadas = [
            "Cuenta Proveedor",
            "Nombre Proveedor",
            "Factura",
            "Fecha documento",
            "TIPO",
        ]
        for columna in columnas_esperadas:
            if columna not in df.columns:
                print(f"⚠️ Falta la columna esperada: {columna}")
                return [], None

        # Elimina filas vacías y filas cuya primera columna esté vacía
        df = df.dropna(how="all")

        if not df.empty:
            primera_columna = df.columns[0]
            df = df[
                df[primera_columna].apply(
                    lambda value: not (pd.isna(value) or str(value).strip() == "")
                )
            ]

        # Elimina filas que contienen encabezados repetidos ("TIPO", "Fecha documento") excepto la primera fila
        if not df.empty and df.shape[1] >= 2:
            header_repetition_mask = df.iloc[:, 0].astype(str).str.strip().eq(
                "TIPO"
            ) & df.iloc[:, 1].astype(str).str.strip().eq("Fecha documento")
            if not header_repetition_mask.empty:
                header_repetition_mask.iloc[0] = False
                df = df[~header_repetition_mask]

        # Eliminar duplicados basados en 'RUT Proveedor', 'Folio' y 'Fecha Docto'
        df = df.drop_duplicates(
            subset=["Cuenta Proveedor", "Factura", "Fecha documento"], keep="first"
        )

        # Convertir cada fila en una instancia de Registro
        registros = [
            Registro(
                rut_proveedor=row["Cuenta Proveedor"],
                razon_social=row["Nombre Proveedor"],
                folio=int(row["Factura"]),
                fecha_docto=row["Fecha documento"],
                area=row["TIPO"],
            )
            for _, row in df.iterrows()
        ]

        return registros, archivo_xlsx
    except Exception as e:
        print(f"⚠️ Error al leer el archivo Excel: {e}")
        return [], None


def extraer_url_desde_xlsx(registros):
    """
    Recorre los registros y lee los archivos CSV (convertidos desde XLSX) descargados para extraer la URL cuando el Folio y Rut Emisor coincidan.
    """
    for registro in registros:
        if not registro.ruta_archivo:  # Si no hay archivo, no procesamos
            registro.estado_url_archivo = False
            registro.url_archivo = None
            continue

        try:
            # Leer el CSV con pandas
            df = pd.read_csv(registro.ruta_archivo, dtype=str)
            print(df.columns)
            df.columns = [col.lower() for col in df.columns]

            # Verificar si las columnas necesarias existen
            columnas_requeridas = ["folio", "rut emisor", "url"]
            if not all(col in df.columns for col in columnas_requeridas):
                print(
                    f"⚠️ El archivo {registro.ruta_archivo} no tiene los encabezados requeridos."
                )
                registro.estado_url_archivo = False
                registro.url_archivo = None
                continue

            # Filtrar por coincidencia de Folio y Rut Emisor
            df_filtrado = df[
                (df["folio"] == str(registro.folio))
                & (df["rut emisor"] == str(registro.rut_proveedor))
            ]

            # Obtener la URL si hay coincidencia
            if not df_filtrado.empty:
                registro.estado_url_archivo = True
                registro.url_archivo = df_filtrado["url"].values[
                    0
                ]  # Tomar la primera coincidencia
                registro.url_archivo = registro.url_archivo.replace(
                    '=HYPERLINK("', ""
                ).replace('")', "")

                print(
                    f"✅ URL encontrada para folio {registro.folio}: {registro.url_archivo}"
                )
            else:
                registro.estado_url_archivo = False
                registro.url_archivo = None
                print(f"❌ No se encontró URL para folio {registro.folio}.")

        except Exception as e:
            print(f"⚠️ Error al procesar {registro.ruta_archivo}: {e}")
            registro.estado_url_archivo = False
            registro.url_archivo = None
