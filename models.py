from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

# Tabla de clientes
class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(50), nullable=False, unique=True)
    telefono = Column(String(15), nullable=False)
    
    # Relación con Barbero (opcional: cliente puede tener un barbero asignado)
    barbero_id = Column(Integer, ForeignKey("barberos.id"), nullable=True)
    barbero = relationship("Barbero", back_populates="clientes")

# Tabla de jefes
class Jefe(Base):
    __tablename__ = "jefes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    usuario = Column(String(20), nullable=False, unique=True)
    contrasena = Column(String(255), nullable=False)
    rol = Column(String(50), nullable=True)

# Tabla de barberos
class Barbero(Base):
    __tablename__ = "barberos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    
    # Relación con clientes
    clientes = relationship("Cliente", back_populates="barbero")

