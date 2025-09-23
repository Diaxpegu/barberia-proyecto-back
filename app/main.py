import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import Cliente, Jefe, Barbero, Servicio, Producto, Disponibilidad, Reserva, Notificacion
from pydantic import BaseModel

# Crear tablas en la BD
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configuración CORS
origins = [
    "https://web-production-23c06.up.railway.app"  # frontend deploy
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo Pydantic para login
class LoginData(BaseModel):
    username: str
    password: str

# Endpoint de login
@app.post("/login/")
@app.post("/login")
def login_jefe(credentials: LoginData):
    db: Session = SessionLocal()
    jefe = db.query(Jefe).filter(Jefe.usuario == credentials.username).first()
    db.close()

    if jefe and jefe.contraseña == credentials.password:
        return {"mensaje": "Login exitoso", "id_jefe": jefe.id_jefe}
    else:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

# Endpoints de clientes, barberos, servicios y productos
@app.get("/clientes/")
def listar_clientes():
    db: Session = SessionLocal()
    clientes = db.query(Cliente).all()
    db.close()
    return clientes

@app.get("/barberos/")
def listar_barberos():
    db: Session = SessionLocal()
    barberos = db.query(Barbero).all()
    db.close()
    return barberos

@app.get("/servicios/")
def listar_servicios():
    db: Session = SessionLocal()
    servicios = db.query(Servicio).all()
    db.close()
    return servicios

@app.get("/productos/")
def listar_productos():
    db: Session = SessionLocal()
    productos = db.query(Producto).all()
    db.close()
    return productos

# Disponibilidad y reservas
@app.get("/disponibilidad/libre/")
def disponibilidad_libre():
    db: Session = SessionLocal()
    bloques = db.query(Disponibilidad).filter(Disponibilidad.estado=="disponible").all()
    db.close()
    return bloques

@app.get("/reservas/pendientes/")
def reservas_pendientes():
    db: Session = SessionLocal()
    reservas = db.query(Reserva).filter(Reserva.estado=="pendiente").all()
    db.close()
    return reservas

@app.put("/disponibilidad/bloquear/{id_disponibilidad}")
def bloquear_disponibilidad(id_disponibilidad: int):
    db: Session = SessionLocal()
    bloque = db.query(Disponibilidad).get(id_disponibilidad)
    if bloque:
        bloque.estado = "bloqueado"
        db.commit()
    db.close()
    return {"mensaje": "Bloqueo realizado"}

@app.put("/reservas/confirmar/{id_reserva}")
def confirmar_reserva(id_reserva: int):
    db: Session = SessionLocal()
    reserva = db.query(Reserva).get(id_reserva)
    if reserva:
        reserva.estado = "confirmado"
        db.commit()
    db.close()
    return {"mensaje": "Reserva confirmada"}

@app.delete("/reservas/cancelar/{id_reserva}")
def cancelar_reserva(id_reserva: int):
    db: Session = SessionLocal()
    reserva = db.query(Reserva).get(id_reserva)
    if reserva:
        db.delete(reserva)
        db.commit()
    db.close()
    return {"mensaje": "Reserva cancelada"}

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

    # Convertir a lista de diccionarios para JSON
    resultado = [
        {
            "id_reserva": r[0],
            "cliente": r[1],
            "barbero": r[2],
            "nombre_servicio": r[3],
            "fecha": str(r[4]),
            "hora": str(r[5]),
        } for r in reservas
    ]
    return resultado

# Ejecutar Uvicorn
if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT)
