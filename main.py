from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId
import os

from database import (
    clientes_col, barberos_col, servicios_col, productos_col,
    reservas_col, disponibilidades_col, jefes_col
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

@app.post("/barberos/")
def crear_barbero(barbero: BarberoSchema):
    nuevo_barbero = {
        "nombre": barbero.nombre,
        "usuario": barbero.usuario,
        "contrasena": barbero.contrasena,
        "especialidades": barbero.especialidades,
        "disponibilidad": barbero.disponibilidad or []
    }

    existente = barberos_col.find_one({"usuario": barbero.usuario})
    if existente:
        raise HTTPException(status_code=400, detail="El usuario ya existe")

    barbero_id = insert_document(barberos_col, nuevo_barbero)
    return {"mensaje": "Barbero creado correctamente", "id": str(barbero_id)}

@app.delete("/barberos/{barbero_id}")
def eliminar_barbero(barbero_id: str):
    try:
        result = barberos_col.delete_one({"_id": ObjectId(barbero_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Barbero no encontrado")
        return {"mensaje": "Barbero eliminado correctamente"}
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

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
    usuario = datos.get("usuario")
    contrasena = datos.get("contrasena")

    if not usuario or not contrasena:
        raise HTTPException(status_code=400, detail="Faltan credenciales")

    jefe = jefes_col.find_one({"usuario": usuario})
    if jefe and jefe["contrasena"] == contrasena:
        return {"mensaje": "Inicio de sesión exitoso", "rol": "jefe", "usuario": usuario}

    barbero = barberos_col.find_one({"usuario": usuario})
    if barbero and barbero["contrasena"] == contrasena:
        return {"mensaje": "Inicio de sesión exitoso", "rol": "barbero", "usuario": barbero["nombre"]}

    raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

@app.get("/")
def root():
    return {"mensaje": "API conectada correctamente a MongoDB (BD test)"}

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
