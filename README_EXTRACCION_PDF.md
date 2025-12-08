# 📄 Extracción de Datos desde PDFs de Facturas

## 📋 Descripción

Este módulo permite extraer automáticamente los montos (Neto, IVA y Total) desde archivos PDF de facturas chilenas (DTE). Los datos extraídos se integran en el flujo principal del sistema y se incluyen en los informes generados.

## 🎯 Características

- ✅ Extracción automática de **Monto Neto**, **Monto IVA** y **Monto Total**
- ✅ Soporte para múltiples formatos de facturas chilenas
- ✅ Validación cruzada de montos (cálculo automático si falta algún valor)
- ✅ Integración con el modelo `Registro` existente
- ✅ Generación de informes Excel con los montos extraídos
- ✅ Soporte para `pdfplumber` y `PyPDF2` como motores de extracción

## 📦 Instalación

### Opción 1: Script Automático (Recomendado)

```bash
cd "Contabilidad/Contabilidad IConstruye"
chmod +x instalar_dependencias.sh
./instalar_dependencias.sh
```

### Opción 2: Manual

```bash
# Crear entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Verificar instalación
python3 -c "import pdfplumber; print('✅ pdfplumber instalado correctamente')"
```

### Opción 3: Sin entorno virtual

```bash
pip3 install --user pdfplumber
```

## 🚀 Uso

### 1. Integración Automática en el Flujo Principal

El módulo ya está integrado en `main.py`. Se ejecuta automáticamente después de descargar los PDFs:

```python
# En main.py, función procesamiento_excel()
descargar_pdf(registros)          # 1. Descarga PDFs
extraer_datos_registros(registros) # 2. NUEVO: Extrae montos
```

### 2. Probar con PDFs Existentes

Procesar todos los PDFs en el directorio de descargas:

```bash
python test_pdf_extractor.py
```

**Salida esperada:**

```
======================================================================
PRUEBA DE EXTRACCIÓN DE DATOS DESDE PDFs
======================================================================
📁 Directorio: ../Descargas/2025-12-05/Facturas PDF

📄 Procesando 15 PDFs en ../Descargas/2025-12-05/Facturas PDF...
   ✓ 1263_COMERCIALIZADORA SERVI SANTIAGO E.I.R.L.pdf: Neto=$1.074.028 | Total=$1.278.093
   ✓ 422_SOC DE TRANSPORTES GUAJARDO Y COMPANIA LTDA.pdf: Neto=$890.000 | Total=$1.059.100
   ...

======================================================================
RESUMEN DETALLADO DE EXTRACCIÓN
======================================================================

📊 Estadísticas:
   Total de PDFs: 15
   ✓ Exitosos: 14
   ❌ Fallidos: 1
   Tasa de éxito: 93.3%
```

### 3. Probar con un PDF Específico

```bash
python test_pdf_extractor.py "../Descargas/2025-12-05/Facturas PDF/1263_COMERCIALIZADORA SERVI SANTIAGO E.I.R.L.pdf"
```

### 4. Uso Programático

```python
from src.services.pdf_extractor import extraer_datos_registros, procesar_pdf_factura

# Opción A: Procesar lista de registros (integrado)
registros = extraer_datos_registros(mis_registros)

# Opción B: Procesar un PDF individual
resultado = procesar_pdf_factura("ruta/al/archivo.pdf")
print(f"Monto Neto: ${resultado['monto_neto']:,}")
print(f"Monto IVA: ${resultado['monto_iva']:,}")
print(f"Monto Total: ${resultado['monto_total']:,}")

# Opción C: Procesar un directorio completo
from src.services.pdf_extractor import extraer_datos_directorio
resultados = extraer_datos_directorio("ruta/al/directorio")
```

## 📊 Campos Agregados al Modelo `Registro`

```python
@dataclass
class Registro:
    # ... campos existentes ...
    
    # Nuevos campos de extracción PDF
    estado_extraccion_pdf: Optional[bool]  # True si extrajo correctamente
    monto_neto: Optional[int]              # Monto neto sin IVA
    monto_iva: Optional[int]               # Monto IVA (19%)
    monto_total: Optional[int]             # Monto total a pagar
    error_extraccion: Optional[str]        # Mensaje de error si falló
    
    def resumen_montos(self) -> str:
        """Retorna resumen formateado de montos"""
        return "Neto: $1.074.028 | IVA: $204.065 | Total: $1.278.093"
```

## 📈 Informes Excel Actualizados

Los informes generados ahora incluyen tres columnas adicionales:

| RUT | Razón Social | Folio | ... | **Monto Neto** | **Monto IVA** | **Monto Total** | URL Drive |
|-----|--------------|-------|-----|----------------|---------------|-----------------|-----------|
| 77088977-4 | COMERCIALIZADORA... | 1263 | ... | 1.074.028 | 204.065 | 1.278.093 | https://... |

## 🔧 Arquitectura del Módulo

```
src/services/pdf_extractor.py
├── extraer_texto_pdf()           # Extrae texto del PDF
├── limpiar_monto()                # Normaliza formato de montos chilenos
├── extraer_montos()               # Busca patrones de montos con regex
├── procesar_pdf_factura()         # Orquesta la extracción completa
├── extraer_datos_registros()      # Procesa lista de Registros
└── extraer_datos_directorio()     # Procesa directorio completo
```

## 🎨 Patrones de Extracción

El módulo reconoce múltiples formatos de facturas chilenas:

### Monto Neto
```
MONTO NETO: $ 1.234.567
NETO: $1.234.567
SUB TOTAL NETO: 1.234.567
VALOR NETO $ 1.234.567
```

### Monto IVA
```
MONTO IVA: $ 234.568
IVA 19%: $234.568
IVA (19%): $ 234.568
I.V.A.: 234.568
```

### Monto Total
```
MONTO TOTAL: $ 1.469.135
TOTAL A PAGAR: $1.469.135
VALOR TOTAL: 1.469.135
TOTAL FACTURA: $ 1.469.135
```

## ✅ Validación de Datos

El módulo incluye validación cruzada automática:

1. **Si tiene Neto e IVA pero no Total**: Calcula Total = Neto + IVA
2. **Si tiene Total e IVA pero no Neto**: Calcula Neto = Total - IVA
3. **Si no encuentra ningún monto**: Marca como error y registra el detalle

## 🐛 Solución de Problemas

### Error: "No se encontró librería para leer PDFs"

```bash
# Verificar instalación
python3 -c "import pdfplumber"

# Si falla, reinstalar
pip install pdfplumber --force-reinstall
```

### Error: "No se pudo extraer texto del PDF"

**Causas posibles:**
- PDF protegido con contraseña
- PDF es una imagen escaneada (no tiene texto real)
- PDF corrupto

**Soluciones:**
1. Verificar que el PDF se pueda abrir normalmente
2. Para PDFs escaneados, se requeriría OCR (fuera del scope actual)
3. Revisar el PDF manualmente

### No se extraen los montos correctamente

**Verificar patrones:**
```bash
# Ejecutar en modo debug para ver el texto extraído
python test_pdf_extractor.py "ruta/al/pdf_problema.pdf"
```

El script mostrará una muestra del texto extraído. Si los montos no coinciden con los patrones esperados, se pueden agregar nuevos patrones en `pdf_extractor.py`, función `extraer_montos()`.

## 📝 Ejemplos de Salida

### Consola (durante ejecución)
```
📄 Iniciando extracción de datos desde PDFs...
   ✓ Folio 1263: Neto=$1.074.028 | IVA=$204.065 | Total=$1.278.093
   ✓ Folio 422: Neto=$890.000 | IVA=$169.100 | Total=$1.059.100
   ⚠ Folio 728: Sin PDF
   ❌ Folio 561: No se encontraron montos en el PDF

============================================================
📄 Extracción completada:
   ✓ Exitosos: 12
   ❌ Fallidos: 2
   ⚠ Sin PDF: 1
============================================================
```

### Objeto Registro actualizado
```python
registro.estado_extraccion_pdf = True
registro.monto_neto = 1074028
registro.monto_iva = 204065
registro.monto_total = 1278093
registro.error_extraccion = None

# Usar el método helper
print(registro.resumen_montos())
# Output: "Neto: $1.074.028 | IVA: $204.065 | Total: $1.278.093"
```

## 🔄 Flujo Completo del Sistema

```
1. Leer Excel con folios → registros[]
2. Hacer scraping → actualizar registros
3. Descargar PDFs → registro.ruta_pdf
4. 🆕 Extraer montos de PDFs → registro.monto_neto/iva/total
5. Subir a Google Drive → registro.drive_url
6. Generar informes Excel (con montos) → informe.xlsx
7. Enviar correos con informes adjuntos
```

## 📚 Documentación API

### `extraer_datos_registros(registros: List[Registro]) -> List[Registro]`

Función principal para integrar en el flujo.

**Parámetros:**
- `registros`: Lista de objetos Registro con campo `ruta_pdf` definido

**Retorna:**
- La misma lista con campos actualizados: `monto_neto`, `monto_iva`, `monto_total`, `estado_extraccion_pdf`

**Efectos secundarios:**
- Modifica los objetos Registro in-place
- Imprime progreso en consola

### `procesar_pdf_factura(ruta_pdf: str) -> Dict[str, Any]`

Procesa un PDF individual.

**Retorna:**
```python
{
    "exito": True,
    "monto_neto": 1074028,
    "monto_iva": 204065,
    "monto_total": 1278093,
    "error": None,
    "texto_extraido": "Factura Electrónica..."
}
```

## 🤝 Contribuir

Para agregar soporte a nuevos formatos de factura:

1. Editar `src/services/pdf_extractor.py`
2. Agregar nuevos patrones en la función `extraer_montos()`
3. Probar con PDFs reales usando `test_pdf_extractor.py`

## 📄 Licencia

Parte del sistema de Contabilidad IConstruye - Santa Elena

---

**Última actualización:** 2025-12-05
**Versión del módulo:** 1.0.0