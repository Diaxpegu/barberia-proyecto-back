from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

class Cliente(BaseModel):
    nombre: str
    correo: EmailStr
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
    fecha: date
    hora_inicio: str
    hora_fin: str
    estado: str
    id_barbero: Optional[str] = None

class Reserva(BaseModel):
    id_cliente: str
    id_barbero: str
    id_servicio: str
    fecha: date
    hora: str
    estado: str