# 🚀 Guía Rápida: Extracción de Datos desde PDFs

## ✅ ¿Qué se implementó?

Se agregó un sistema completo para **extraer montos** (Neto, IVA, Total) desde archivos PDF de facturas chilenas.

### Archivos Creados/Modificados:

1. ✅ **`src/models/registro.py`** - Agregados campos: `monto_neto`, `monto_iva`, `monto_total`, `estado_extraccion_pdf`
2. ✅ **`src/services/pdf_extractor.py`** - Nuevo módulo completo de extracción
3. ✅ **`src/services/excel_generator.py`** - Actualizados informes con columnas de montos
4. ✅ **`main.py`** - Integrada extracción en el flujo principal
5. ✅ **`requirements.txt`** - Agregada dependencia `pdfplumber`
6. ✅ **`test_pdf_extractor.py`** - Script de pruebas
7. ✅ **`instalar_dependencias.sh`** - Script de instalación

---

## 📦 Instalación (PRIMER PASO)

### Opción A: Automática (Recomendado)

```bash
cd "Contabilidad/Contabilidad IConstruye"
./instalar_dependencias.sh
```

### Opción B: Manual

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Opción C: Instalación simple

```bash
pip3 install --user pdfplumber
```

---

## 🧪 Probar la Extracción

### Probar con los PDFs existentes:

```bash
cd "Contabilidad/Contabilidad IConstruye"
python test_pdf_extractor.py
```

**Esto procesará todos los PDFs en:**
`../Descargas/2025-12-05/Facturas PDF/`

### Probar con un PDF específico:

```bash
python test_pdf_extractor.py "ruta/al/archivo.pdf"
```

---

## 🎯 Uso en Producción

### El flujo ya está integrado automáticamente:

```python
# En main.py - NO necesitas modificar nada
def procesamiento_excel(driver, registros):
    procesar_folios(driver, registros)
    extraer_url_desde_xlsx(registros)
    descargar_pdf(registros)
    
    # ⭐ NUEVO: Extracción automática de montos
    extraer_datos_registros(registros)
    
    return registros
```

### Ejecutar el sistema completo:

```bash
python main.py
```

**El sistema ahora:**
1. Descarga PDFs
2. 🆕 Extrae montos (Neto, IVA, Total)
3. Sube a Google Drive
4. Genera informes Excel **con los montos extraídos**
5. Envía correos

---

## 📊 Resultado

### Los registros ahora tienen:

```python
registro.monto_neto = 1074028      # Extraído del PDF
registro.monto_iva = 204065        # Extraído del PDF
registro.monto_total = 1278093     # Extraído del PDF
registro.estado_extraccion_pdf = True
```

### Los informes Excel incluyen 3 columnas nuevas:

| ... | Monto Neto | Monto IVA | Monto Total | URL Drive |
|-----|------------|-----------|-------------|-----------|
| ... | 1.074.028  | 204.065   | 1.278.093   | https://  |

---

## 📝 Salida de Ejemplo

```
📄 Iniciando extracción de datos desde PDFs...
   ✓ Folio 1263: Neto=$1.074.028 | IVA=$204.065 | Total=$1.278.093
   ✓ Folio 422: Neto=$890.000 | IVA=$169.100 | Total=$1.059.100
   ✓ Folio 3876: Neto=$750.500 | IVA=$142.595 | Total=$893.095
   ⚠ Folio 728: Sin PDF
   ❌ Folio 561: No se encontraron montos en el PDF

============================================================
📄 Extracción completada:
   ✓ Exitosos: 12
   ❌ Fallidos: 2
   ⚠ Sin PDF: 1
============================================================
```

---

## 🔧 Uso Programático

```python
from src.services.pdf_extractor import (
    extraer_datos_registros,
    procesar_pdf_factura,
    extraer_datos_directorio
)

# Opción 1: Procesar lista de registros
registros_actualizados = extraer_datos_registros(mis_registros)

# Opción 2: Procesar un PDF individual
resultado = procesar_pdf_factura("factura.pdf")
print(f"Total: ${resultado['monto_total']:,}")

# Opción 3: Procesar directorio completo
resultados = extraer_datos_directorio("./pdfs/")
for r in resultados:
    print(f"{r['archivo']}: ${r['monto_total']:,}")
```

---

## ❓ Solución de Problemas

### Error: "No se encontró librería para leer PDFs"

```bash
pip install pdfplumber
# o
pip3 install --user pdfplumber
```

### No se extraen montos

1. Ejecutar en modo debug:
   ```bash
   python test_pdf_extractor.py "archivo_problema.pdf"
   ```

2. Verificar texto extraído en la salida

3. Si el formato es diferente, agregar patrones en:
   `src/services/pdf_extractor.py` → función `extraer_montos()`

### PDFs escaneados (imágenes)

Los PDFs que son imágenes escaneadas **no funcionarán** porque no tienen texto real. 
Se requeriría OCR (fuera del alcance actual).

---

## 📚 Documentación Completa

Ver: `README_EXTRACCION_PDF.md`

---

## ✨ Características

- ✅ Extrae automáticamente Monto Neto, IVA y Total
- ✅ Soporta múltiples formatos de facturas chilenas
- ✅ Validación cruzada (calcula valores faltantes)
- ✅ Integrado en el flujo principal
- ✅ Incluido en informes Excel
- ✅ Manejo robusto de errores
- ✅ Script de pruebas independiente

---

## 🎉 ¡Listo para Usar!

1. Instalar dependencias: `./instalar_dependencias.sh`
2. Probar: `python test_pdf_extractor.py`
3. Ejecutar: `python main.py`

**Los informes ahora incluyen automáticamente los montos extraídos de los PDFs.**

---

📅 **Implementado:** 2025-12-05  
🔖 **Versión:** 1.0.0