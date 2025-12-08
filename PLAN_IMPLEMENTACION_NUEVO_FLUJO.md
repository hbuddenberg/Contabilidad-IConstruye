# 📋 PLAN DE IMPLEMENTACIÓN: Nuevo Flujo de Informes
## Sistema de Actualización de Excel Original con Datos Extraídos

**Fecha de creación:** 2025-12-08  
**Estado:** ✅ COMPLETADO  
**Versión:** 1.0.0

---

## 🎯 OBJETIVO

Cambiar el sistema actual de múltiples informes agrupados por área a un **único archivo Excel** que:
1. Se **copia** desde `Por Hacer/` a `informes/`
2. Se **actualiza** con las nuevas columnas de datos extraídos (Q en adelante)
3. Se **renombra** con fecha y hora de ejecución
4. Se **envía** a un único destinatario desde `config.yaml`
5. **Ambos archivos** (original y actualizado) se **mueven a procesados** en carpeta con fecha/hora

---

## 📊 COMPARACIÓN: ANTES vs DESPUÉS

| Aspecto | Antes ❌ | Después ✅ |
|---------|----------|-----------|
| Agrupación | Por área | Sin agrupación |
| Archivos generados | Múltiples (1 por área) | 1 único archivo |
| Origen del archivo | Crear nuevo Excel | Copiar y actualizar original |
| Nombre de salida | `informe_resumen_{area}_{fecha}.xlsx` | `{nombre}_{fecha}_{hora}.xlsx` |
| Destinatarios | Múltiples (por área) | Único (config.yaml) |
| Carpeta procesados | `Descargas/2025-12-08/` | `Descargas/2025-12-08_20.00/` |

---

## 🔄 FLUJO COMPLETO

```
1. LEER Excel original (Por Hacer/)
         ↓
2. SCRAPING en IConstruye
         ↓
3. EXTRAER URLs y DESCARGAR PDFs
         ↓
4. EXTRAER MONTOS desde PDFs
         ↓
5. SUBIR a Google Drive
         ↓
6. COPIAR Excel original a informes/ (con timestamp)
         ↓
7. ACTUALIZAR copia con columnas Q-U
         ↓
8. ENVIAR correo a destinatario único
         ↓
9. MOVER AMBOS archivos a Descargas/{timestamp}/
```

---

## 📁 ESTRUCTURA FINAL DE ARCHIVOS

```
Descargas/2025-12-08_20.00/
├── SEMANA 40 copy.xlsx                    ← Original (backup)
├── SEMANA 40 copy_2025-12-08_20.00.xlsx   ← Actualizado (columnas Q-U)
├── Facturas PDF/                          ← PDFs descargados
└── *.csv                                  ← CSVs descargados
```

---

## 📊 COLUMNAS NUEVAS (Q-U)

| Columna | Nombre | Fuente |
|---------|--------|--------|
| Q | Monto Neto Factura | `registro.monto_neto` |
| R | Monto IVA Factura | `registro.monto_iva` |
| S | Monto Total Factura | `registro.monto_total` |
| T | Estado Subida Factura | `registro.estado_subida` |
| U | URL Factura | `registro.drive_url` |

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Paso 1: Configuración
- [x] 1.1 Modificar `config.yaml` - Agregar `destinatario_informe` ✅

### Paso 2: Nuevo Módulo
- [x] 2.1 Crear `src/services/excel_updater.py` ✅
  - [x] Función `copiar_y_actualizar_excel()` ✅
  - [x] Función `_generar_nombre_con_timestamp()` ✅
  - [x] Función `_encontrar_fila_registro()` ✅
  - [x] Función `_agregar_encabezados()` ✅
  - [x] Función `_escribir_datos_registro()` ✅

### Paso 3: Modificar main.py
- [x] 3.1 Agregar import de `excel_updater` ✅
- [x] 3.2 Eliminar imports no necesarios (`grouping`, `excel_generator`) ✅
- [x] 3.3 Agregar función `enviar_informe_unico()` ✅
- [x] 3.4 Agregar función `mover_archivos_procesados()` ✅
- [x] 3.5 Simplificar función `main()` ✅
- [x] 3.6 Eliminar funciones obsoletas (`generar_informe_area`, `asignacion_correo`) ✅

### Paso 4: Pruebas
- [ ] 4.1 Probar copia de archivo
- [ ] 4.2 Probar actualización de columnas
- [ ] 4.3 Probar envío de correo
- [ ] 4.4 Probar movimiento de archivos
- [ ] 4.5 Prueba de flujo completo

### Paso 5: Limpieza
- [ ] 5.1 Actualizar documentación
- [ ] 5.2 Deprecar archivos no usados

---

## ✅ RESUMEN DE IMPLEMENTACIÓN COMPLETADA

### Archivos Creados:
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `src/services/excel_updater.py` | 361 | Módulo para copiar y actualizar Excel |

### Archivos Modificados:
| Archivo | Cambio |
|---------|--------|
| `config.yaml` | Agregado `destinatario_informe` |
| `main.py` | Nuevo flujo simplificado de 7 pasos |

### Funciones Nuevas en main.py:
- `enviar_informe_unico()` - Envía correo a destinatario único
- `mover_archivos_procesados()` - Mueve ambos archivos a carpeta fecha/hora

### Funciones Eliminadas de main.py:
- `generar_informe_area()` - Ya no se agrupa por área
- `asignacion_correo()` - Ya no se envía por área

### Imports Eliminados:
- `from src.services.excel_generator import generar_informe_excel_con_urls_drive`
- `from src.utils.grouping import agrupar_por_area`
- `asignar_correos_a_areas`, `generar_contenido_html`

### Imports Agregados:
- `from src.services.excel_updater import copiar_y_actualizar_excel`

---

## 📝 REGISTRO DE CAMBIOS

### [Completado] Paso 1: Configuración

**Archivo:** `config.yaml`  
**Cambio:** Agregar campo `destinatario_informe`  
**Estado:** ✅ Completado

```yaml
correo:
  destinatario_informe: "ltarrillo@santaelena.com"  # ← NUEVO
  cc: hans.buddenberg@smart-bots.cl
  cco: h.buddenberg@gmail.com
```

---

### [Completado] Paso 2: Crear excel_updater.py

**Archivo:** `src/services/excel_updater.py`  
**Estado:** ✅ Completado

**Funciones creadas:**
- `copiar_y_actualizar_excel()` - Función principal (361 líneas total)
- `_generar_nombre_con_timestamp()` - Genera nombre con fecha/hora
- `_encontrar_fila_registro()` - Mapea registro a fila Excel
- `_agregar_encabezados()` - Agrega encabezados columnas Q-U
- `_escribir_datos_registro()` - Escribe datos en celdas Q-U
- `obtener_resumen_actualizacion()` - Genera estadísticas

---

### [Completado] Paso 3: Modificar main.py

**Archivo:** `main.py`  
**Estado:** ✅ Completado

**Cambios realizados:**
1. ✅ Import de `copiar_y_actualizar_excel` desde `excel_updater`
2. ✅ Eliminado import de `excel_generator` y `grouping`
3. ✅ Eliminado imports de `asignar_correos_a_areas` y `generar_contenido_html`
4. ✅ Nueva función `enviar_informe_unico()` - Envía a destinatario único
5. ✅ Nueva función `mover_archivos_procesados()` - Mueve ambos archivos a carpeta fecha/hora
6. ✅ Función `main()` simplificada con flujo de 7 pasos
7. ✅ Eliminadas funciones `generar_informe_area()` y `asignacion_correo()`

---

## 🔧 DETALLES TÉCNICOS

### Timestamp Único
```python
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H.%M")
# Ejemplo: "2025-12-08_20.00"
```

### Mapeo Registro → Fila
```python
# Clave única: RUT + Folio + Fecha
mascara = (
    (df["Cuenta Proveedor"] == registro.rut_proveedor) &
    (df["Factura"].astype(str) == str(registro.folio)) &
    (df["Fecha documento"] == registro.fecha_docto)
)
```

### Formato de Montos
```python
celda.number_format = "#,##0"  # Formato chileno con separador de miles
```

---

## ⚠️ NOTAS IMPORTANTES

1. **Preservar formato:** Al abrir con openpyxl, se mantienen estilos existentes
2. **Hora en nombre:** Usar `.` en lugar de `:` (no válido en nombres de archivo)
3. **Archivos vacíos al final:** `Por Hacer/` e `informes/` quedan vacíos
4. **Backup automático:** El archivo original se preserva en procesados

---

## 📞 SOPORTE

Si encuentras problemas durante la implementación:
1. Verificar que el archivo original existe en `Por Hacer/`
2. Verificar permisos de escritura en `informes/` y `Descargas/`
3. Verificar que `config.yaml` tiene `destinatario_informe`

---

## 🚀 CÓMO PROBAR

```bash
cd "Contabilidad/Contabilidad IConstruye"
python main.py
```

**Resultado esperado:**
1. Lee archivo de `Por Hacer/`
2. Hace scraping en IConstruye
3. Descarga PDFs y extrae montos
4. Sube a Google Drive
5. Crea copia actualizada en `informes/`
6. Envía correo a `ltarrillo@santaelena.com`
7. Mueve archivos a `Descargas/2025-12-08_20.00/`

---

**Última actualización:** 2025-12-08  
**Estado:** ✅ Implementación completada - Pendiente pruebas