from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Registro:
    rut_proveedor: str
    razon_social: str
    folio: int
    fecha_docto: str
    area: str
    estado_folio: Optional[bool] = field(
        default=None
    )  # True si el folio fue encontrado, False si no
    estado_descarga: Optional[bool] = field(
        default=None
    )  # True si el Excel fue descargado, False si no
    ruta_archivo: Optional[str] = field(default=None)  # Ruta del archivo descargado
    estado_url_archivo: Optional[bool] = field(
        default=None
    )  # True si se encontró la URL en el archivo, False si no
    url_archivo: Optional[str] = field(
        default=None
    )  # Valor de la URL encontrada en el archivo
    estado_pdf: Optional[bool] = field(
        default=None
    )  # True si el PDF fue descargado correctamente, False si no
    ruta_pdf: Optional[str] = field(default=None)  # Ruta del archivo PDF descargado
    tipo_archivo: Optional[str] = field(
        default=None
    )  # Tipo de archivo subido (PDF, Excel, CSV, etc.)
    estado_subida: Optional[bool] = field(
        default=None
    )  # True si se subió a Drive correctamente
    drive_url: Optional[str] = field(default=None)  # URL de acceso al archivo en Drive
    ruta_drive: Optional[str] = field(default=None)  # Ruta completa en Drive
    error: Optional[str] = field(
        default=None
    )  # Mensaje de error si hubo fallo en la subida

    def __str__(self):
        estado_folio = "Encontrado" if self.estado_folio else "No encontrado"
        estado_descarga = "Descargado" if self.estado_descarga else "No descargado"
        estado_url = "URL Encontrada" if self.estado_url_archivo else "No encontrada"
        estado_drive = "Subido" if self.estado_subida else "No subido"
        return f"Registro(Folio: {self.folio} RUT: {self.rut_proveedor}, Estado: {estado_folio}, Descarga: {estado_descarga}, {estado_url}, Drive: {estado_drive}, Archivo: {self.ruta_archivo})"
