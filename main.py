import os
<<<<<<< HEAD
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import schemas, crud

# crea tablas si no existen (en prod usar migraciones como alembic)
=======
from fastapi import FastAPI
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import Cliente, Jefe, Barbero, Servicio, Producto, Disponibilidad, Reserva, Notificacion

# Crear tablas en la BD
>>>>>>> f6990b1 (Modificar main.py y models.py con tablas según el diccionario de datos)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Clientes")

<<<<<<< HEAD
# CORS configurable por variable de entorno (separa orígenes con coma)
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# dependencia DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/clientes", response_model=List[schemas.ClienteOut])
def listar_clientes(db: Session = Depends(get_db)):
    return crud.get_clientes(db)

@app.get("/clientes/{cliente_id}", response_model=schemas.ClienteOut)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = crud.get_cliente(db, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente

@app.post("/clientes", response_model=schemas.ClienteOut, status_code=201)
def crear_cliente(cliente: schemas.ClienteCreate, db: Session = Depends(get_db)):
    return crud.create_cliente(db, cliente)

=======
# Listar todos los clientes
@app.get("/clientes/")
def listar_clientes():
    db: Session = SessionLocal()
    clientes = db.query(Cliente).all()
    db.close()
    return clientes

#  Listar barberos
@app.get("/barberos/")
def listar_barberos():
    db: Session = SessionLocal()
    barberos = db.query(Barbero).all()
    db.close()
    return barberos

#  Listar servicios
@app.get("/servicios/")
def listar_servicios():
    db: Session = SessionLocal()
    servicios = db.query(Servicio).all()
    db.close()
    return servicios

# Listar productos
@app.get("/productos/")
def listar_productos():
    db: Session = SessionLocal()
    productos = db.query(Producto).all()
    db.close()
    return productos

# Disponibilidad libre
@app.get("/disponibilidad/libre/")
def disponibilidad_libre():
    db: Session = SessionLocal()
    bloques = db.query(Disponibilidad).filter(Disponibilidad.estado=="disponible").all()
    db.close()
    return bloques

# Reservas pendientes
@app.get("/reservas/pendientes/")
def reservas_pendientes():
    db: Session = SessionLocal()
    reservas = db.query(Reserva).filter(Reserva.estado=="pendiente").all()
    db.close()
    return reservas

#  Bloquear horario de barbero
@app.put("/disponibilidad/bloquear/{id_disponibilidad}")
def bloquear_disponibilidad(id_disponibilidad: int):
    db: Session = SessionLocal()
    bloque = db.query(Disponibilidad).get(id_disponibilidad)
    if bloque:
        bloque.estado = "bloqueado"
        db.commit()
    db.close()
    return {"mensaje": "Bloqueo realizado"}

#  Confirmar reserva
@app.put("/reservas/confirmar/{id_reserva}")
def confirmar_reserva(id_reserva: int):
    db: Session = SessionLocal()
    reserva = db.query(Reserva).get(id_reserva)
    if reserva:
        reserva.estado = "confirmado"
        db.commit()
    db.close()
    return {"mensaje": "Reserva confirmada"}

# Cancelar reserva
@app.delete("/reservas/cancelar/{id_reserva}")
def cancelar_reserva(id_reserva: int):
    db: Session = SessionLocal()
    reserva = db.query(Reserva).get(id_reserva)
    if reserva:
        db.delete(reserva)
        db.commit()
    db.close()
    return {"mensaje": "Reserva cancelada"}

# Reservas con detalle completo
@app.get("/reservas/detalle/")
def reservas_detalle():
    db: Session = SessionLocal()
    reservas = db.query(
        Reserva.id_reserva,
        Cliente.nombre.label("cliente"),
        Barbero.nombre.label("barbero"),
        Servicio.nombre_servicio,
        Reserva.fecha,
        Reserva.hora
    ).join(Cliente, Reserva.id_cliente == Cliente.id_cliente
    ).join(Barbero, Reserva.id_barbero == Barbero.id_barbero
    ).join(Servicio, Reserva.id_servicio == Servicio.id_servicio).all()
    db.close()
    return reservas
>>>>>>> f6990b1 (Modificar main.py y models.py con tablas según el diccionario de datos)

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
