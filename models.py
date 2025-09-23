from sqlalchemy import Column, Integer, String, Numeric, Enum, Date, Time, DateTime, ForeignKey
from database import Base

class Cliente(Base):
    __tablename__ = "clientes"
    id_cliente = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(255), nullable=False)
    telefono = Column(String(15), nullable=False)

class Jefe(Base):
    __tablename__ = "jefes"
    id_jefe = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    usuario = Column(String(20), nullable=False)
    contrasena = Column(String(255), nullable=False) 
    rol = Column(String(30))

class Barbero(Base):
    __tablename__ = "barberos"
    id_barbero = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    especialidad = Column(String(50))
    usuario = Column(String(20), nullable=False)
    contrasena = Column(String(255), nullable=False)
    id_jefe = Column(Integer, ForeignKey("jefes.id_jefe"), nullable=False)

class Servicio(Base):
    __tablename__ = "servicios"
    id_servicio = Column(Integer, primary_key=True, index=True)
    nombre_servicio = Column(String(50), nullable=False)
    precio = Column(Numeric(10,2), nullable=False)
    duracion = Column(Integer, nullable=False)  
    id_jefe = Column(Integer, ForeignKey("jefes.id_jefe"), nullable=False)

class Producto(Base):
    __tablename__ = "productos"
    id_producto = Column(Integer, primary_key=True, index=True)
    nombre_producto = Column(String(150), nullable=False)
    descripcion = Column(String(500))
    precio = Column(Numeric(10,2), nullable=False)
    id_jefe = Column(Integer, ForeignKey("jefes.id_jefe"), nullable=False)

class Disponibilidad(Base):
    __tablename__ = "disponibilidades"
    id_disponibilidad = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    estado = Column(Enum('disponible','bloqueado', name='estado_disponibilidad'), nullable=False)
    id_barbero = Column(Integer, ForeignKey("barberos.id_barbero"), nullable=False)

class Reserva(Base):
    __tablename__ = "reservas"
    id_reserva = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    hora = Column(Time, nullable=False)
    estado = Column(Enum('pendiente','confirmado','cancelado','realizado', name='estado_reserva'), nullable=False)
    id_cliente = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=False)
    id_barbero = Column(Integer, ForeignKey("barberos.id_barbero"), nullable=False)
    id_servicio = Column(Integer, ForeignKey("servicios.id_servicio"), nullable=False)
    id_disponibilidad = Column(Integer, ForeignKey("disponibilidades.id_disponibilidad"), nullable=False)

class Notificacion(Base):
    __tablename__ = "notificaciones"
    id_notificacion = Column(Integer, primary_key=True, index=True)
    fecha_envio = Column(DateTime, nullable=False)
    tipo = Column(Enum('confirmado','recordatorio','cancelado', name='tipo_notificacion'), nullable=False)
    id_reserva = Column(Integer, ForeignKey("reservas.id_reserva"), nullable=False)
