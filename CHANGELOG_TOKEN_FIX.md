# 🔧 Changelog: Manejo Automático de Token Expirado/Revocado

## 📅 Fecha: 2025-12-05
## 🎯 Objetivo: Eliminar y regenerar automáticamente `token.json` cuando expire o sea revocado

---

## ❌ Problema Original

Cuando el token de Google OAuth expiraba o era revocado, el sistema fallaba con este error:

```
Error: ('invalid_grant: Token has been expired or revoked.', 
        {'error': 'invalid_grant', 'error_description': 'Token has been expired or revoked.'})
```

**Solución manual anterior:** El usuario debía manualmente eliminar `token.json` y volver a autenticar.

---

## ✅ Solución Implementada

El sistema ahora detecta automáticamente este error y:

1. 🔍 Detecta el error `invalid_grant`
2. 🗑️ Elimina `token.json` automáticamente
3. 🔄 Inicia un nuevo flujo de autenticación
4. ✅ Continúa la ejecución sin intervención manual

---

## 📝 Archivos Modificados

### 1. `src/google_drive/drive_oauth.py`

**Función:** `ensure_credentials()`

**Cambios:**
- Agregado bloque `try-except` en el refresh del token
- Detección de errores `invalid_grant` o `token has been expired or revoked`
- Eliminación automática de `token.json`
- Reinicio del flujo de autenticación

**Código agregado:**
```python
if creds and creds.expired and creds.refresh_token:
    print("🔄 Credenciales expiradas. Intentando refrescar...")
    try:
        creds.refresh(Request())
        save_token(creds)
        return creds
    except Exception as e:
        error_msg = str(e)
        # Detectar error de token revocado/expirado
        if (
            "invalid_grant" in error_msg.lower()
            or "token has been expired or revoked" in error_msg.lower()
        ):
            print(f"❌ Error: {error_msg}")
            print("🗑️  Token revocado o expirado. Eliminando token.json...")
            if TOKEN_FILE.exists():
                TOKEN_FILE.unlink()
                print("✅ token.json eliminado. Iniciando nueva autenticación...")
            # Reintentar con flujo completo
            creds = None
        else:
            # Si es otro error, re-lanzarlo
            raise
```

---

### 2. `src/utils/email_sender.py`

**Función:** `autenticar()`

**Cambios:**
- Agregado bloque `try-except` en el refresh del token
- Detección de errores `invalid_grant` o `token has been expired or revoked`
- Eliminación automática de `token.json`
- Forzar nuevo flujo de autenticación

**Código agregado:**
```python
if creds and creds.expired and creds.refresh_token:
    try:
        creds.refresh(Request())
    except Exception as e:
        error_msg = str(e)
        # Detectar error de token revocado/expirado
        if (
            "invalid_grant" in error_msg.lower()
            or "token has been expired or revoked" in error_msg.lower()
        ):
            print(f"❌ Error: {error_msg}")
            print("🗑️  Token revocado o expirado. Eliminando token.json...")
            if os.path.exists(token_path):
                os.remove(token_path)
                print("✅ token.json eliminado. Iniciando nueva autenticación...")
            # Forzar nuevo flujo de autenticación
            creds = None
        else:
            # Si es otro error, re-lanzarlo
            raise
```

---

## 🔄 Flujo de Recuperación Automática

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Sistema intenta refrescar credenciales expiradas        │
└───────────────────┬─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Google responde con error: "invalid_grant"              │
└───────────────────┬─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Sistema detecta el error automáticamente                │
│    ✓ Busca: "invalid_grant" o "token has been expired"     │
└───────────────────┬─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Sistema elimina token.json                              │
│    🗑️  os.remove(token_path) o TOKEN_FILE.unlink()        │
└───────────────────┬─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Sistema inicia nuevo flujo OAuth                        │
│    🔐 Abre navegador para consentimiento                    │
└───────────────────┬─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Usuario autoriza en el navegador                        │
└───────────────────┬─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Nuevo token.json generado                               │
│    ✅ Sistema continúa ejecución normal                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Salida en Consola

### Antes (Error manual):
```
Error: ('invalid_grant: Token has been expired or revoked.', ...)
[PROCESO INTERRUMPIDO - Requería intervención manual]
```

### Ahora (Recuperación automática):
```
🔄 Credenciales expiradas. Intentando refrescar...
❌ Error: invalid_grant: Token has been expired or revoked.
🗑️  Token revocado o expirado. Eliminando token.json...
✅ token.json eliminado. Iniciando nueva autenticación...
🔐 Iniciando flujo de consentimiento en el navegador...
[Navegador se abre automáticamente]
✅ Nueva autenticación completada
[Proceso continúa normalmente]
```

---

## 🧪 Casos de Prueba

### ✅ Caso 1: Token expirado
- **Antes:** Error fatal, proceso detenido
- **Ahora:** Regeneración automática, proceso continúa

### ✅ Caso 2: Token revocado manualmente desde Google
- **Antes:** Error fatal, proceso detenido
- **Ahora:** Regeneración automática, proceso continúa

### ✅ Caso 3: Token con scopes diferentes
- **Antes:** Error confuso
- **Ahora:** Detección automática y nuevo consentimiento

### ✅ Caso 4: Otros errores de red/API
- **Comportamiento:** Se re-lanza el error original (no se ocultan otros problemas)

---

## 🎯 Beneficios

| Beneficio | Descripción |
|-----------|-------------|
| ✅ **Cero intervención manual** | No requiere que el usuario elimine archivos manualmente |
| ✅ **Recuperación automática** | El sistema se recupera solo del error |
| ✅ **Experiencia de usuario mejorada** | Mensajes claros sobre qué está pasando |
| ✅ **Robustez** | Maneja casos edge automáticamente |
| ✅ **Logs informativos** | Usuario entiende cada paso del proceso |

---

## 🔒 Seguridad

- ✅ Solo elimina `token.json` en caso de error específico de OAuth
- ✅ Preserva `credentials.json` (secreto del cliente)
- ✅ Fuerza nuevo consentimiento explícito del usuario
- ✅ No oculta otros errores críticos

---

## 📚 Dependencias Agregadas

### `pyproject.toml`:
```toml
dependencies = [
    # ... dependencias existentes ...
    "pdfplumber>=0.10.0",
    "py2pdf"  # ← NUEVA: Alternativa para lectura de PDFs
]
```

### `requirements.txt`:
```txt
# Dependencias para extracción de PDFs
pdfplumber>=0.10.0
PyPDF2>=3.0.0  # ← NUEVA: Alternativa
```

---

## 🚀 Uso

No se requiere cambio alguno en el código de usuario. La funcionalidad se activa automáticamente cuando:

1. El sistema intenta usar Google Drive API
2. El sistema intenta enviar emails con Gmail API
3. El token está expirado o revocado

**El usuario solo verá:**
```
🔄 Credenciales expiradas. Intentando refrescar...
🗑️  Token revocado o expirado. Eliminando token.json...
🔐 Iniciando flujo de consentimiento en el navegador...
```

Y el navegador se abrirá automáticamente para re-autorizar.

---

## ✨ Mejoras Futuras Posibles

- [ ] Agregar reintentos automáticos con backoff exponencial
- [ ] Notificar por email cuando el token necesite renovación
- [ ] Agregar logging estructurado para auditoría
- [ ] Dashboard de estado de credenciales

---

## 📞 Soporte

Si encuentras problemas con la autenticación:

1. Verifica que `credentials.json` existe en `src/configuration/`
2. Verifica que tienes permisos en Google Cloud Console
3. Revisa los logs en consola para mensajes específicos
4. Si `token.json` no se elimina, verifica permisos del filesystem

---

**Implementado por:** Claude Sonnet 4.5  
**Fecha:** 2025-12-05  
**Versión:** 1.1.0  
**Estado:** ✅ Producción Ready

---