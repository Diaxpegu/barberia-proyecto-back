from pydantic import BaseModel
from typing import Optional

class ClienteSchema(BaseModel):
    nombre: str
    correo: str
    telefono: str
    direccion: Optional[str] = None

class BarberoSchema(BaseModel):
    nombre: str
    especialidad: Optional[str] = None

class ServicioSchema(BaseModel):
    nombre_servicio: str
    precio: float
    duracion: int
    id_jefe: Optional[str] = None

class ProductoSchema(BaseModel):
    nombre_producto: str
    precio: float
    stock: int
    id_jefe: Optional[str] = None

class DisponibilidadSchema(BaseModel):
    fecha: str
    hora_inicio: str
    hora_fin: str
    estado: str
    id_barbero: Optional[str] = None

class ReservaSchema(BaseModel):
    id_cliente: str
    id_barbero: str
    id_servicio: str
    fecha: str
    hora: str
    estado: str
