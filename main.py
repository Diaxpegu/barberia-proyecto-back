from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId
from database import (
    clientes_col, barberos_col, servicios_col, productos_col,
    reservas_col, disponibilidades_col
)
from models import Cliente, Barbero, Servicio, Producto, Disponibilidad, Reserva
from crud import to_json
import os

app = FastAPI()

# --- CORS ---
origins = ["https://web-production-23c06.up.railway.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CLIENTES ---
@app.get("/clientes/")
def listar_clientes():
    return [to_json(c) for c in clientes_col.find()]

@app.post("/clientes/")
def crear_cliente(cliente: Cliente):
    res = clientes_col.insert_one(cliente.dict())
    return {"mensaje": "Cliente agregado", "id": str(res.inserted_id)}

# --- BARBEROS ---
@app.get("/barberos/")
def listar_barberos():
    return [to_json(b) for b in barberos_col.find()]

# --- SERVICIOS ---
@app.get("/servicios/")
def listar_servicios():
    return [to_json(s) for s in servicios_col.find()]

# --- PRODUCTOS ---
@app.get("/productos/")
def listar_productos():
    return [to_json(p) for p in productos_col.find()]

# --- DISPONIBILIDAD ---
@app.get("/disponibilidad/libre/")
def disponibilidad_libre():
    return [to_json(d) for d in disponibilidades_col.find({"estado": "disponible"})]

@app.put("/disponibilidad/bloquear/{id_disponibilidad}")
def bloquear_disponibilidad(id_disponibilidad: str):
    result = disponibilidades_col.update_one(
        {"_id": ObjectId(id_disponibilidad)},
        {"$set": {"estado": "bloqueado"}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No encontrada")
    return {"mensaje": "Bloqueo realizado"}

# --- RESERVAS ---
@app.get("/reservas/pendientes/")
def reservas_pendientes():
    return [to_json(r) for r in reservas_col.find({"estado": "pendiente"})]

@app.put("/reservas/confirmar/{id_reserva}")
def confirmar_reserva(id_reserva: str):
    result = reservas_col.update_one(
        {"_id": ObjectId(id_reserva)},
        {"$set": {"estado": "confirmado"}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No encontrada")
    return {"mensaje": "Reserva confirmada"}

@app.delete("/reservas/cancelar/{id_reserva}")
def cancelar_reserva(id_reserva: str):
    result = reservas_col.delete_one({"_id": ObjectId(id_reserva)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No encontrada")
    return {"mensaje": "Reserva cancelada"}

@app.get("/reservas/detalle/")
def reservas_detalle():
    reservas = list(reservas_col.aggregate([
        {"$lookup": {"from": "clientes", "localField": "id_cliente", "foreignField": "_id", "as": "cliente"}},
        {"$lookup": {"from": "barberos", "localField": "id_barbero", "foreignField": "_id", "as": "barbero"}},
        {"$lookup": {"from": "servicios", "localField": "id_servicio", "foreignField": "_id", "as": "servicio"}}
    ]))
    return [to_json(r) for r in reservas]

@app.get("/")
def root():
    return {"mensaje": "API conectada correctamente a MongoDB"}

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
