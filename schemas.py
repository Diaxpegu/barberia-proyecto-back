#schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date

class ClienteSchema(BaseModel):
    nombre: str
    correo: EmailStr
    telefono: str
    direccion: Optional[str] = None

class DisponibilidadSchema(BaseModel):
    fecha: date
    hora_inicio: str
    hora_fin: str
    estado: str = "disponible"
    id_barbero: Optional[str] = None 

class BarberoSchema(BaseModel):
    nombre: str
    especialidad: Optional[str] = None
    usuario: str
    contrasena: str
    disponibilidades: Optional[List[DisponibilidadSchema]] = []

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

class ReservaSchema(BaseModel):
    id_cliente: str
    id_barbero: str
    id_servicio: str
    fecha: date
    hora: str
    estado: str