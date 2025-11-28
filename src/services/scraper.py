import yaml
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import datetime
import glob
import shutil
import zipfile
import xml.etree.ElementTree as ET
import csv
import re

# Cargar configuración desde config.yaml usando ruta absoluta
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

LOGIN_URL = config["web_scraping"]["login_url"]
USUARIO = config["web_scraping"]["usuario"]
CLAVE = config["web_scraping"]["clave"]
CHROMEDRIVER_PATH = config["web_scraping"]["chromedriver_path"]

MAX_INTENTOS = 2  # Número máximo de intentos de login

def iniciar_sesion():
    """
    Inicia sesión en la página web usando Selenium con hasta 2 intentos.
    Configura la carpeta de descargas personalizada con la fecha del día.
    """
    options = Options()
    options.add_experimental_option("detach", True)  # Evita que el navegador se cierre automáticamente

    # Crear la subcarpeta con la fecha del día

    carpeta_con_fecha = os.path.join(config["web_scraping"]["carpeta_descargas"])
    os.makedirs(carpeta_con_fecha, exist_ok=True)

    # Configurar la carpeta de descargas en Selenium
    prefs = {
        "download.default_directory": carpeta_con_fecha,
        "download.prompt_for_download": False,  # No preguntar dónde guardar
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    service = Service(config["web_scraping"]["chromedriver_path"])

    intentos = 0

    intentos = 0
    while intentos <= MAX_INTENTOS:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(LOGIN_URL)

        try:
            # Esperar y hacer clic en "Ingresa con tu correo"
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "liTabLoginSso"))
            ).click()
            print("✅ Clic en 'Ingresa con tu correo' realizado correctamente.")

            # Esperar y escribir el usuario
            input_usuario = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "txtUsuarioSso"))
            )
            input_usuario.send_keys(USUARIO)
            print("✅ Usuario ingresado.")

            # Esperar y escribir la contraseña
            input_clave = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "txtPasswordSso"))
            )
            input_clave.send_keys(CLAVE)
            print("✅ Contraseña ingresada.")

            # Esperar y hacer clic en "Inicia sesión"
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "btnIniciaSessionSso"))
            ).click()
            print("✅ Clic en 'Inicia sesión' realizado.")
            time.sleep(5)
            return driver  # Devolvemos el driver autenticado
            '''
            # Esperar para verificar si la sesión fue exitosa
            time.sleep(5)  # Espera adicional para carga
            if WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "pnlIndicadores"))
            ):
                print("✅ Inicio de sesión exitoso. Elemento de validación encontrado.")
                return driver  # Devolvemos el driver autenticado
            '''
        except Exception as e:
            print(f"⚠️ Intento {intentos + 1} de inicio de sesión fallido: {e}")
            driver.quit()
            intentos += 1

    print("❌ No se pudo iniciar sesión después de varios intentos. Se enviará un correo.")
    return None  # Devuelve None si falla


def navegar_a_nueva_version(driver):
    """
    Navega directamente a la nueva versión.
    Si falla, devuelve False.
    """
    try:
        cerrar_modal(driver)
        url_nueva_version = "https://cl.iconstruye.com/ICHUB/core.aspx?pagina=recepcion"
        print(f"✅ Navegando a: {url_nueva_version}")
        driver.get(url_nueva_version)

        # Esperar a que la página cargue correctamente
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        print("✅ Acceso a la nueva versión realizado correctamente.")
        return True  # Éxito

    except Exception as e:
        print(f"⚠️ No se pudo acceder a la nueva versión: {e}")
        return False  # Falla


def navegar_a_ultima_pagina(driver):
    """
    Navega a la última página y verifica si el campo de búsqueda está presente.
    Si no está, reintenta hasta 2 veces.
    Si falla, devuelve False.
    """
    url_final = "https://apps.iconstruye.com/Ichub/Recepcionnewversion.aspx?authFromAgilice=true&modo=2"
    intentos = 0
    max_intentos = 2  

    while intentos <= max_intentos:
        try:
            cerrar_modal(driver)
            print(f"✅ Intento {intentos + 1}: Navegando a la última página: {url_final}")
            driver.get(url_final)

            # Verificar si el campo de búsqueda está presente
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "txtBusquedaFolio"))
            )
            print("✅ Navegación exitosa, campo de búsqueda encontrado.")
            return True  # Éxito

        except Exception as e:
            print(f"⚠️ No se encontró el campo de búsqueda. Intento {intentos + 1} fallido: {e}")
            intentos += 1

    print("❌ No se pudo ingresar a la última página después de varios intentos. Se enviará un correo.")
    return False  # Falla


def buscar_folio(driver, folio):
    """
    Busca un folio en la web haciendo clic en el botón de búsqueda y devuelve True si se encuentra, False si no.
    """
    try:
        time.sleep(3)
        cerrar_modal(driver)
        # Esperar a que el campo de búsqueda esté presente
        input_folio = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "txtBusquedaFolio"))
        )
        
        # Limpiar el campo antes de escribir (por si hay texto previo)
        input_folio.clear()
        input_folio.send_keys(folio)

        # Hacer clic en el botón de búsqueda
        btn_buscar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "buscar"))  # Ajusta el ID si es otro
        )
        btn_buscar.click()

        # Esperar la respuesta de la web (puede ser un mensaje de error o una tabla con resultados)
        time.sleep(1)  # Espera breve para carga

        # Verificar si hay un mensaje de "No encontrado"
        mensaje_no_encontrado = driver.find_elements(By.XPATH, "//div[@class='content-message-no-found']//p[contains(text(), 'No se han encontrado documentos')]")
        
        if mensaje_no_encontrado:
            print(f"❌ Folio {folio} NO encontrado.")
            return False  # El folio no existe en la web

        
        print(f"✅ Folio {folio} encontrado.")
        return True  # El folio sí existe en la web

    except Exception as e:
        print(f"⚠️ Error al buscar folio {folio}: {e}")
        return False  # En caso de error, asumimos que el folio no existe


def procesar_folios(driver, registros):
    """
    Recorre los folios, los busca en la web y actualiza su estado de búsqueda y descarga.
    """
    for registro in registros:
        cerrar_modal(driver)
        folio = registro.folio  # Obtener el folio de la instancia
        encontrado = buscar_folio(driver, folio)  # Buscar el folio

        # Actualizar estado de búsqueda en la instancia
        registro.estado_folio = encontrado

        # Si el folio fue encontrado, intentar descargar el archivo Excel
        if encontrado:
            registro.estado_descarga = descargar_excel(driver, registro)
        else:
            registro.estado_descarga = False

        # Mostrar resultado en consola
        estado_folio = "✅ Encontrado" if encontrado else "❌ No encontrado"
        estado_descarga = "✅ Descargado" if registro.estado_descarga else "❌ No descargado"
        print(f"{estado_folio} | {estado_descarga} - Folio: {folio}")

    print("\n✅ Búsqueda y descargas completadas. Todos los estados han sido actualizados.")





def limpiar_carpeta_descargas():
    """
    Elimina todos los archivos .xlsx en la carpeta base antes de iniciar una nueva descarga.
    """
    
    carpeta_base = config["web_scraping"]["carpeta_descargas"]
    archivos = glob.glob(os.path.join(carpeta_base, "*.xlsx"))

    for archivo in archivos:
        try:
            os.remove(archivo)
            print(f"🗑️ Eliminado archivo previo: {archivo}")
        except Exception as e:
            print(f"⚠️ No se pudo eliminar {archivo}: {e}")

import os
import time
import shutil
import datetime
import glob
from xlsx2csv import Xlsx2csv

def descargar_excel(driver, registro):
    """
    Descarga el archivo Excel en la carpeta base, luego lo mueve y renombra en la carpeta con fecha del día.
    Convierte el archivo XLSX a CSV y almacena la ruta del CSV en la clase Registro.
    """
    try:
        cerrar_modal(driver)
        fecha_hoy = datetime.datetime.now().strftime("%Y-%m-%d")
        carpeta_base = config["web_scraping"]["carpeta_descargas"]
        carpeta_con_fecha = os.path.join(carpeta_base, fecha_hoy)
        os.makedirs(carpeta_con_fecha, exist_ok=True)

        # Nombre final esperado
        nombre_xlsx = f"{registro.rut_proveedor}_{registro.folio}.xlsx"
        destino_xlsx = os.path.join(carpeta_con_fecha, nombre_xlsx)

        # Limpiar la carpeta base antes de la descarga
        limpiar_carpeta_descargas()

        # Hacer clic en el botón de descarga
        btn_descargar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "btnDescargarExcel"))
        )
        btn_descargar.click()
        print(f"✅ Descarga iniciada para folio {registro.folio}.")

        # Esperar la descarga (máximo 20 segundos)
        tiempo_espera = 0
        archivo_descargado = None

        while tiempo_espera < 20:
            archivos = glob.glob(os.path.join(carpeta_base, "*.xlsx"))
            if archivos:
                archivo_descargado = max(archivos, key=os.path.getctime)  # Último archivo descargado
                break
            time.sleep(1)
            tiempo_espera += 1

        if not archivo_descargado:
            print(f"❌ No se pudo descargar el archivo para el folio {registro.folio}.")
            registro.estado_descarga = False
            return False  # Descarga fallida

        # Mover el archivo descargado a la carpeta con la fecha del día
        shutil.move(archivo_descargado, destino_xlsx)
        print(f"✅ Archivo movido correctamente: {destino_xlsx}")

        # Convertir XLSX a CSV
        nombre_csv = destino_xlsx.replace(".xlsx", ".csv")
        
        xlsx_to_csv(destino_xlsx, nombre_csv)
        print(f"✅ Archivo convertido a CSV: {nombre_csv}")

        # Eliminar el archivo XLSX original
        os.remove(destino_xlsx)
        print(f"🗑️ Archivo XLSX eliminado: {destino_xlsx}")

        # Guardar la ruta del CSV en el objeto Registro
        registro.estado_descarga = True
        registro.ruta_archivo = nombre_csv
    
        return True  # Descarga exitosa
        

    except Exception as e:
        print(f"⚠️ Error al descargar o convertir el archivo para folio {registro.folio}: {e}")
        registro.estado_descarga = False
        return False  # Descarga fallida

    
    
    
def cerrar_modal(driver):
    """
    Intenta cerrar el modal de feedback sin verificar si está presente.
    Si el modal no existe, simplemente no hace nada.
    """
    try:
        # Intentar hacer clic en el botón de cierre
        boton_cerrar = driver.find_element(By.CLASS_NAME, "btn-close-feedback")
        boton_cerrar.click()

        # Esperar a que el modal desaparezca (opcional)
        WebDriverWait(driver, 3).until(
            EC.invisibility_of_element((By.CLASS_NAME, "modal-dialog"))
        )

        print("✅ Modal cerrado correctamente.")

    except Exception:
        # Si el modal no está presente, no pasa nada
        pass






def column_index_from_string(col_str):
    """Convierte letras de columna (ej. 'A', 'BC') a un índice numérico (1-indexado)."""
    index = 0
    for c in col_str:
        index = index * 26 + (ord(c) - ord('A') + 1)
    return index

def parse_shared_strings(zipf):
    """Parsea el archivo sharedStrings.xml y devuelve una lista de strings."""
    shared_strings = []
    try:
        with zipf.open("xl/sharedStrings.xml") as f:
            tree = ET.parse(f)
            root = tree.getroot()
            ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for si in root.findall("ns:si", ns):
                # Algunos strings se dividen en múltiples elementos <t>
                texts = [t.text for t in si.findall(".//ns:t", ns) if t.text]
                shared_strings.append("".join(texts))
    except KeyError:
        # El archivo no existe (no hay strings compartidos)
        pass
    return shared_strings

def parse_sheet(zipf, shared_strings, sheet_filename):
    """Parsea la hoja indicada y devuelve una lista de listas con los datos.
       Si una celda tiene fórmula (<f>), se guarda el contenido de la fórmula como texto."""
    with zipf.open(sheet_filename) as f:
        tree = ET.parse(f)
        root = tree.getroot()
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        # Diccionario para almacenar los datos: clave fila (número), valor dict{columna: valor}
        rows = {}
        for row in root.findall(".//ns:row", ns):
            r_idx = int(row.get("r"))
            rows[r_idx] = {}
            for cell in row.findall("ns:c", ns):
                cell_ref = cell.get("r")
                m = re.match(r"([A-Z]+)(\d+)", cell_ref)
                if m:
                    col_letters = m.group(1)
                    col_num = column_index_from_string(col_letters)
                else:
                    continue  # Si no se puede interpretar la referencia, saltamos

                # Si la celda tiene fórmula, la extraemos
                f_elem = cell.find("ns:f", ns)
                if f_elem is not None and f_elem.text is not None:
                    cell_value = f_elem.text
                else:
                    # Si no tiene fórmula, buscamos el valor (<v>)
                    v_elem = cell.find("ns:v", ns)
                    if v_elem is not None and v_elem.text is not None:
                        # Si la celda es de tipo "s" (shared string), se usa la lista de shared strings
                        if cell.get("t") == "s":
                            idx = int(v_elem.text)
                            cell_value = shared_strings[idx] if idx < len(shared_strings) else ""
                        else:
                            cell_value = v_elem.text
                    else:
                        cell_value = ""
                rows[r_idx][col_num] = cell_value

        # Determinar dimensiones máximas
        max_row = max(rows.keys()) if rows else 0
        max_col = 0
        for r in rows.values():
            if r:
                max_col = max(max_col, max(r.keys()))
        # Construir la lista de listas (matriz)
        data = []
        for i in range(1, max_row + 1):
            row_data = []
            for j in range(1, max_col + 1):
                if i in rows and j in rows[i]:
                    row_data.append(rows[i][j])
                else:
                    row_data.append("")
            data.append(row_data)
        return data

def xlsx_to_csv(xlsx_file, csv_file, sheet_filename="xl/worksheets/sheet1.xml"):
    with zipfile.ZipFile(xlsx_file) as zipf:
        shared_strings = parse_shared_strings(zipf)
        data = parse_sheet(zipf, shared_strings, sheet_filename)
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in data:
            writer.writerow(row)
    print(f"CSV generado exitosamente en '{csv_file}'.")