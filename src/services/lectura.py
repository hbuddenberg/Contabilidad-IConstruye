

import zipfile
import xml.etree.ElementTree as ET
import csv
import re

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

# Uso:
xlsx_to_csv("C:/Users/junio/Documents/SmartBots/Contabilidad/Descargas/Documentos.xlsx", "C:/Users/junio/Documents/SmartBots/Contabilidad/Descargas/PAP.csv")
