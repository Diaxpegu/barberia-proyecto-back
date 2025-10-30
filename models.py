from pydantic import BaseModel
from typing import Optional

class Cliente(BaseModel):
    nombre: str
    correo: str
    telefono: str
    direccion: Optional[str] = None

class Barbero(BaseModel):
    nombre: str
    especialidad: Optional[str] = None

class Servicio(BaseModel):
    nombre_servicio: str
    precio: float
    duracion: int
    id_jefe: Optional[str] = None

class Producto(BaseModel):
    nombre_producto: str
    precio: float
    stock: int
    id_jefe: Optional[str] = None

class Disponibilidad(BaseModel):
    fecha: str
    hora_inicio: str
    hora_fin: str
    estado: str
    id_barbero: Optional[str] = None

class Reserva(BaseModel):
    id_cliente: str
    id_barbero: str
    id_servicio: str
    fecha: str
    hora: str
    estado: str
