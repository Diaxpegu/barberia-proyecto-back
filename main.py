from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bson import errors
import os

from database import (
    clientes_col, barberos_col, servicios_col, productos_col,
    reservas_col, disponibilidades_col
)
from crud import to_json, get_by_id, insert_document, update_document, delete_document
from schemas import (
    ClienteSchema, BarberoSchema, ServicioSchema, ProductoSchema,
    DisponibilidadSchema, ReservaSchema
)

app = FastAPI()

# Configuración CORS

origins = ["https://barberia-proyecto-front-production-3f2e.up.railway.app/", 
           "https://barberia-proyecto-back-production-f876.up.railway.app/"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CLIENTES

@app.get("/clientes/")
def listar_clientes():
    clientes = list(clientes_col.find({}, {"_id": 0}))
    return clientes

@app.post("/clientes/")
def crear_cliente(cliente: ClienteSchema):
    cliente_id = insert_document(clientes_col, cliente.dict())
    return {"mensaje": "Cliente agregado", "id": cliente_id}

# BARBEROS

@app.get("/barberos/")
def listar_barberos():
    return [to_json(b) for b in barberos_col.find()]

@app.post("/barberos/")
def crear_barbero(barbero: BarberoSchema):
    barbero_id = insert_document(barberos_col, barbero.dict())
    return {"mensaje": "Barbero agregado", "id": barbero_id}

# SERVICIOS

@app.get("/servicios/")
def listar_servicios():
    return [to_json(s) for s in servicios_col.find()]

@app.post("/servicios/")
def crear_servicio(servicio: ServicioSchema):
    servicio_id = insert_document(servicios_col, servicio.dict())
    return {"mensaje": "Servicio agregado", "id": servicio_id}

# PRODUCTOS

@app.get("/productos/")
def listar_productos():
    return [to_json(p) for p in productos_col.find()]

@app.post("/productos/")
def crear_producto(producto: ProductoSchema):
    producto_id = insert_document(productos_col, producto.dict())
    return {"mensaje": "Producto agregado", "id": producto_id}

# DISPONIBILIDADES

@app.get("/disponibilidad/libre/")
def disponibilidad_libre():
    return [to_json(d) for d in disponibilidades_col.find({"estado": "disponible"})]

@app.put("/disponibilidad/bloquear/{id_disponibilidad}")
def bloquear_disponibilidad(id_disponibilidad: str):
    modified_count = update_document(disponibilidades_col, id_disponibilidad, {"estado": "bloqueado"})
    if modified_count == 0:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")
    return {"mensaje": "Bloqueo realizado"}

@app.post("/disponibilidad/")
def crear_disponibilidad(disponibilidad: DisponibilidadSchema):
    disp_id = insert_document(disponibilidades_col, disponibilidad.dict())
    return {"mensaje": "Disponibilidad agregada", "id": disp_id}

# RESERVAS

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

@app.post("/reservas/")
def crear_reserva(reserva: ReservaSchema):
    reserva_id = insert_document(reservas_col, reserva.dict())
    return {"mensaje": "Reserva agregada", "id": reserva_id}

@app.get("/reservas/detalle/")
def reservas_detalle():
    reservas = list(reservas_col.aggregate([
        {"$lookup": {"from": "clientes", "localField": "id_cliente", "foreignField": "_id", "as": "cliente"}},
        {"$lookup": {"from": "barberos", "localField": "id_barbero", "foreignField": "_id", "as": "barbero"}},
        {"$lookup": {"from": "servicios", "localField": "id_servicio", "foreignField": "_id", "as": "servicio"}}
    ]))
    return [to_json(r) for r in reservas]


# ROOT

@app.get("/")
def root():
    return {"mensaje": "API conectada correctamente a MongoDB (BD test)"}


# UVICORN

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)

