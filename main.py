from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

from database import (
    clientes_col, barberos_col, servicios_col, productos_col,
    reservas_col, disponibilidades_col, admin_col
)
from crud import to_json, insert_document, update_document, delete_document
from schemas import (
    ClienteSchema, BarberoSchema, ServicioSchema, ProductoSchema,
    DisponibilidadSchema, ReservaSchema
)

app = FastAPI(title="API Barbería", version="1.0.0")

origins = [
    "https://barberia-proyecto-front-production-3f2e.up.railway.app",
    "https://barberia-proyecto-back-production-f876.up.railway.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/clientes/")
def listar_clientes():
    clientes = list(clientes_col.find({}, {"_id": 0}))
    return clientes

@app.get("/barberos/")
def listar_barberos():
    return [to_json(b) for b in barberos_col.find()]

@app.get("/servicios/")
def listar_servicios():
    return [to_json(s) for s in servicios_col.find()]

@app.get("/productos/")
def listar_productos():
    return [to_json(p) for p in productos_col.find()]

@app.get("/disponibilidad/libre/")
def disponibilidad_libre():
    barberos = list(barberos_col.find())
    disponibles = []
    for b in barberos:
        for disp in b.get("disponibilidad", []):
            if disp.get("estado") == "disponible":
                disponibles.append({
                    "_id": str(b["_id"]),
                    "nombre": b["nombre"],
                    "especialidades": b.get("especialidades", []),
                    "fecha": disp.get("fecha"),
                    "hora_inicio": disp.get("hora_inicio"),
                    "hora_fin": disp.get("hora_fin"),
                    "estado": disp.get("estado")
                })
                break
    return disponibles

@app.put("/disponibilidad/bloquear/{id_disponibilidad}")
def bloquear_disponibilidad(id_disponibilidad: str):
    modified_count = update_document(disponibilidades_col, id_disponibilidad, {"estado": "bloqueado"})
    if modified_count == 0:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")
    return {"mensaje": "Bloqueo realizado"}

@app.get("/reservas/pendientes/")
def reservas_pendientes():
    return [to_json(r) for r in reservas_col.find({"estado": "pendiente"})]

@app.put("/reservas/confirmar/{id_reserva}")
def confirmar_reserva(id_reserva: str):
    modified_count = update_document(reservas_col, id_reserva, {"estado": "confirmado"})
    if modified_count == 0:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return {"mensaje": "Reserva confirmada"}

@app.delete("/reservas/cancelar/{id_reserva}")
def cancelar_reserva(id_reserva: str):
    deleted_count = delete_document(reservas_col, id_reserva)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return {"mensaje": "Reserva cancelada"}

@app.get("/reservas/detalle/")
def reservas_detalle():
    reservas = list(reservas_col.aggregate([
        {"$lookup": {"from": "clientes", "localField": "id_cliente", "foreignField": "_id", "as": "cliente"}},
        {"$lookup": {"from": "barberos", "localField": "id_barbero", "foreignField": "_id", "as": "barbero"}},
        {"$lookup": {"from": "servicios", "localField": "id_servicio", "foreignField": "_id", "as": "servicio"}}
    ]))
    return [to_json(r) for r in reservas]

@app.post("/login/")
def login(datos: dict):
    """Verifica si el usuario existe como admin o barbero."""
    usuario = datos.get("usuario")
    contrasena = datos.get("contrasena")

    if not usuario or not contrasena:
        raise HTTPException(status_code=400, detail="Faltan credenciales")

    # Buscar en administradores
    admin = admin_col.find_one({"usuario": usuario})
    if admin and admin["contrasena"] == contrasena:
        return {"mensaje": "Login exitoso", "rol": "admin", "usuario": usuario}

    # Buscar en barberos
    barbero = barberos_col.find_one({"usuario": usuario})
    if barbero and barbero["contrasena"] == contrasena:
        return {"mensaje": "Login exitoso", "rol": "barbero", "usuario": barbero["nombre"]}

    raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

@app.get("/")
def root():
    return {"mensaje": "API conectada correctamente a MongoDB (BD test)"}

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
