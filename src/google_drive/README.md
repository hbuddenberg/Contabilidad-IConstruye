# Google Drive Package

Paquete de Python para interactuar con Google Drive: autenticación OAuth, subida/descarga de archivos, y gestión de carpetas.

## Instalación

Las dependencias ya están incluidas en el `pyproject.toml` del proyecto:

```bash
uv sync
```

## Estructura del Paquete

```
src/google_drive/
├── __init__.py           # Exporta todas las funciones principales
├── drive_oauth.py        # Autenticación y operaciones básicas
├── drive_upload.py       # Subida de archivos con estructura de carpetas
├── main.py              # CLI para subir directorios
└── ejemplo_uso.py       # Ejemplos de uso
```

## Uso Básico

### 1. Importar desde otros módulos

```python
from google_drive import (
    ensure_credentials,
    build_drive_service,
    upload_directory_to_drive,
    upload_file_to_drive,
    ensure_drive_folder,
    generate_share_link,
)
```

### 2. Subir un directorio completo

```python
from google_drive import upload_directory_to_drive

resultado = upload_directory_to_drive(
    nombre="SantaElena",           # Carpeta raíz en Drive
    fecha="2025-11-27",            # Subcarpeta (opcional, usa fecha actual si no se especifica)
    directorio="./downloads",      # Directorio local
    parent_id="root",              # ID de carpeta padre en Drive
    recursivo=False                # Incluir subdirectorios
)

print(f"Subidos {resultado['total_archivos']} archivos")
for archivo in resultado['archivos']:
    print(f"{archivo['archivo']}: {archivo['url_compartida']}")
```

### 3. Control manual (paso a paso)

```python
from google_drive import (
    ensure_credentials,
    build_drive_service,
    ensure_drive_folder,
    upload_file_to_drive,
    generate_share_link,
)
from pathlib import Path

# Autenticar
creds = ensure_credentials()
service = build_drive_service(creds)

# Crear carpetas
carpeta_raiz = ensure_drive_folder(service, "SantaElena", parent_id="root")
carpeta_fecha = ensure_drive_folder(service, "2025-11-27", parent_id=carpeta_raiz["id"])

# Subir archivo
archivo = upload_file_to_drive(
    service=service,
    local_path=Path("./documento.pdf"),
    parent_id=carpeta_fecha["id"]
)

# Generar enlace compartido
metadata = generate_share_link(service, archivo["id"])
print(f"URL compartida: {metadata['share_url']}")
```

### 4. Usar DriveUploadConfig para mayor control

```python
from google_drive import DriveUploadConfig, upload_to_drive
from pathlib import Path

config = DriveUploadConfig(
    root_folder_name="SantaElena",
    date_folder_name="2025-11-27",
    parent_id="root",
    recursive=False,
    local_base_dir=Path("./downloads")
)

# Subir archivos específicos
archivos = [
    Path("./downloads/archivo1.pdf"),
    Path("./downloads/archivo2.csv"),
]

resultado = upload_to_drive(config=config, files=archivos)
```

## CLI

El módulo incluye un CLI para subir directorios desde la terminal:

```bash
# Subir directorio con fecha actual
uv run python src/google_drive/main.py --nombre "SantaElena" --directorio ./downloads

# Especificar fecha personalizada
uv run python src/google_drive/main.py --nombre "SantaElena" --fecha "2025-11-27" --directorio ./downloads

# Incluir subdirectorios
uv run python src/google_drive/main.py --nombre "SantaElena" --directorio ./downloads --recursivo

# Guardar resumen en JSON
uv run python src/google_drive/main.py --nombre "SantaElena" --directorio ./downloads --output resultado.json
```

## Funciones Disponibles

### Autenticación

- `ensure_credentials()` - Obtiene credenciales OAuth válidas
- `build_drive_service(creds)` - Crea el cliente de Google Drive API
- `save_token(creds)` - Guarda el token en disco
- `load_token(scopes)` - Carga el token desde disco

### Operaciones de Drive

- `list_all_drives_files(service)` - Lista archivos en todas las unidades
- `resolve_path_to_id(service, path)` - Resuelve una ruta a un file ID
- `download_file_by_id(service, file_id, download_dir)` - Descarga un archivo
- `ensure_drive_folder(service, folder_name, parent_id)` - Crea/obtiene una carpeta
- `upload_file_to_drive(service, local_path, parent_id)` - Sube un archivo
- `generate_share_link(service, file_id)` - Genera enlace compartido

### Operaciones de Alto Nivel

- `upload_directory_to_drive(nombre, fecha, directorio)` - Sube un directorio completo
- `upload_to_drive(config, files)` - Sube archivos con configuración personalizada
- `find_local_files(directory, recursive)` - Encuentra archivos en un directorio
- `summarize_upload_to_json(summary)` - Serializa resumen a JSON

## Clases

### DriveUploadConfig

```python
@dataclass
class DriveUploadConfig:
    root_folder_name: str              # Nombre de carpeta raíz
    date_folder_name: Optional[str]    # Nombre de subcarpeta (default: fecha actual)
    parent_id: str = "root"           # ID de carpeta padre
    recursive: bool = False            # Incluir subdirectorios
    local_base_dir: Path = Path(".")  # Directorio base local
```

### UploadedFileSummary

```python
@dataclass
class UploadedFileSummary:
    file_id: str                      # ID del archivo en Drive
    file_name: str                    # Nombre del archivo
    drive_path: str                   # Ruta en Drive
    share_url: Optional[str]          # URL compartida
    mime_type: Optional[str]          # Tipo MIME
    local_path: str                   # Ruta local absoluta
    local_relative_path: str          # Ruta relativa
    timestamp_context: str            # Timestamp UTC
    folder_created: bool              # Si se creó la carpeta de fecha
    root_folder_created: bool         # Si se creó la carpeta raíz
```

## Configuración

### Autenticación OAuth

1. Coloca tu archivo `client_secrets.json` en `src/google_drive/secrets/`
2. La primera ejecución abrirá el navegador para autorizar
3. El token se guardará en `src/google_drive/token.json`

### Scopes

El paquete usa el scope `https://www.googleapis.com/auth/drive` que permite:
- Leer archivos
- Crear y modificar archivos
- Gestionar carpetas
- Generar enlaces compartidos

## Ejemplos Completos

Ver `ejemplo_uso.py` para ejemplos detallados de:
- Subida de directorio completo
- Control manual paso a paso
- Uso de DriveUploadConfig
- Manejo de errores y edge cases

## Notas

- Los archivos nativos de Google (Docs/Sheets/Slides) no se descargan automáticamente
- Los accesos directos (shortcuts) se resuelven automáticamente al archivo real
- Las carpetas se crean automáticamente si no existen
- Los enlaces compartidos son de solo lectura por defecto
