import os
from fastapi import FastAPI, HTTPException, Body
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import Cliente, Jefe, Barbero, Servicio, Producto, Disponibilidad, Reserva, Notificacion

# Crear tablas en la BD
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Endpoint de login
@app.post("/login/")
def login_jefe(username: str = Body(...), password: str = Body(...)):
    db: Session = SessionLocal()
    jefe = db.query(Jefe).filter(Jefe.usuario == username).first()
    db.close()
    
    if jefe and jefe.contraseña == password:
        return {"mensaje": "Login exitoso", "id_jefe": jefe.id_jefe}
    else:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
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

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
