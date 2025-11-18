from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId, errors
from datetime import datetime, timedelta, date
from pydantic import BaseModel
from typing import Optional
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

# ⭐ IMPORTANTE → Importar el scheduler
from scheduler import iniciar_scheduler

app = FastAPI(title="API Barbería", version="1.9.0")

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


# --------------------------------------------------------
# INICIO DEL PROYECTO (EVENTO STARTUP)
# --------------------------------------------------------
@app.on_event("startup")
def startup_event():
    """
    Este evento se ejecuta cuando tu API se inicia.
    Aquí arrancamos el scheduler que enviará correos automáticamente.
    """
    iniciar_scheduler()


# --------------------------------------------------------
# Resto de tu código tal cual estaba
# --------------------------------------------------------

class LoginSchema(BaseModel):
    usuario: str
    contrasena: str


class ReservaCreate(BaseModel):
    id_barbero: str
    fecha: str
    hora: str
    id_cliente: Optional[str] = None
    id_servicio: Optional[str] = None
    nombre_cliente: Optional[str] = None
    apellido_cliente: Optional[str] = None
    email_cliente: Optional[str] = None
    telefono_cliente: Optional[str] = None
    rut_cliente: Optional[str] = None
    servicio_nombre: Optional[str] = None


@app.get("/")
def root():
    return {"mensaje": "API conectada correctamente a MongoDB (BD test)"}


@app.post("/login/")
def login(datos_login: LoginSchema):
    barbero = barberos_col.find_one({"usuario": datos_login.usuario})
    if barbero and barbero["contrasena"] == datos_login.contrasena:
        return {"usuario": barbero["usuario"], "rol": "barbero", "_id": str(barbero["_id"])}
    jefe = jefes_col.find_one({"usuario": datos_login.usuario})
    if jefe and jefe["contrasena"] == datos_login.contrasena:
        return {"usuario": jefe["usuario"], "rol": "jefe", "_id": str(jefe["_id"])}
    raise HTTPException(status_code=404, detail="Usuario o contraseña incorrectos")


@app.get("/clientes/")
def listar_clientes():
    return [to_json(c) for c in clientes_col.find()]


@app.post("/clientes/")
def crear_cliente(cliente: ClienteSchema):
    if clientes_col.find_one({"correo": cliente.correo}):
        raise HTTPException(status_code=400, detail="El cliente ya existe")
    cid = insert_document(clientes_col, cliente.dict())
    return {"mensaje": "Cliente creado correctamente", "id": str(cid)}


@app.get("/barberos/")
def listar_barberos():
    barberos_lista = []
    for b in barberos_col.find():
        data = to_json(b)
        data.pop("contrasena", None)
        data["especialidad"] = data.get("especialidad") or "No asignada"
        if isinstance(data.get("disponibilidades"), list):
            data["disponibilidades"] = f"{len(data['disponibilidades'])} horarios"
        barberos_lista.append(data)
    return barberos_lista


@app.get("/barberos/{barbero_id}")
def obtener_barbero(barbero_id: str):
    try:
        b = barberos_col.find_one({"_id": ObjectId(barbero_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    if not b:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")
    data = to_json(b)
    data.pop("contrasena", None)
    data["especialidad"] = data.get("especialidad") or "No asignada"
    return data


@app.put("/barberos/{barbero_id}")
def actualizar_barbero(barbero_id: str, data: dict = Body(...)):
    try:
        campos = {}
        if "nombre" in data:
            campos["nombre"] = data["nombre"]
        if "especialidad" in data:
            campos["especialidad"] = data["especialidad"]
        if not campos:
            raise HTTPException(status_code=400, detail="Nada para actualizar")
        res = barberos_col.update_one({"_id": ObjectId(barbero_id)}, {"$set": campos})
        if res.modified_count == 0:
            raise HTTPException(status_code=404, detail="Barbero no encontrado o sin cambios")
        return {"mensaje": "Perfil actualizado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/barberos/{barbero_id}/disponibilidades")
def disponibilidades_por_barbero(barbero_id: str):
    try:
        b = barberos_col.find_one({"_id": ObjectId(barbero_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    if not b:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")
    return [d for d in b.get("disponibilidades", []) if "fecha" in d and "hora" in d]


@app.post("/barberos/")
def crear_barbero(barbero: BarberoSchema):
    if barberos_col.find_one({"usuario": barbero.usuario}):
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    hoy = datetime.now().date()
    disponibilidades = []
    for i in range(7):
        fecha = (hoy + timedelta(days=i)).isoformat()
        for hora in ["08:00","09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00"]:
            disponibilidades.append({"fecha": fecha, "hora": hora, "estado": "disponible"})
    nuevo = {
        "nombre": barbero.nombre,
        "usuario": barbero.usuario,
        "contrasena": barbero.contrasena,
        "especialidad": barbero.especialidad or "No asignada",
        "disponibilidades": disponibilidades
    }
    bid = insert_document(barberos_col, nuevo)
    return {"mensaje": "Barbero creado correctamente", "id": str(bid)}


@app.delete("/barberos/{barbero_id}")
def eliminar_barbero(barbero_id: str):
    r = barberos_col.delete_one({"_id": ObjectId(barbero_id)})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")
    return {"mensaje": "Barbero eliminado correctamente"}


@app.get("/servicios/")
def listar_servicios():
    return [to_json(s) for s in servicios_col.find()]


@app.get("/productos/")
def listar_productos():
    return [to_json(p) for p in productos_col.find()]


@app.put("/disponibilidad/bloquear/{barbero_id}/{fecha}/{hora}")
def bloquear_disponibilidad(barbero_id: str, fecha: str, hora: str):
    r = barberos_col.update_one(
        {"_id": ObjectId(barbero_id), "disponibilidades": {"$elemMatch": {"fecha": fecha, "hora": hora}}},
        {"$set": {"disponibilidades.$.estado": "ocupado"}}
    )
    if r.modified_count == 0:
        raise HTTPException(status_code=404, detail="No se encontró esa hora disponible")
    return {"mensaje": "Horario bloqueado correctamente"}


@app.post("/reservas/")
def crear_reserva(reserva: ReservaCreate):
    try:
        barbero_oid = ObjectId(reserva.id_barbero)
        fecha_str = str(reserva.fecha)
        cliente_oid = None

        if reserva.id_cliente and reserva.id_cliente.strip() != "":
            try:
                cliente_oid = ObjectId(reserva.id_cliente)
            except Exception:
                cliente_oid = None

        if not cliente_oid:
            if not reserva.nombre_cliente or not reserva.email_cliente or not reserva.telefono_cliente:
                raise HTTPException(status_code=400, detail="Faltan datos del cliente")
            cliente_doc = {
                "nombre": f"{reserva.nombre_cliente.strip()} {reserva.apellido_cliente.strip() if reserva.apellido_cliente else ''}".strip(),
                "correo": reserva.email_cliente.strip(),
                "telefono": reserva.telefono_cliente.strip(),
                "direccion": None
            }
            existente = clientes_col.find_one({"correo": cliente_doc["correo"]})
            if existente:
                cliente_oid = existente["_id"]
            else:
                cliente_oid = insert_document(clientes_col, cliente_doc)

        servicio_oid = None
        if reserva.id_servicio and reserva.id_servicio.strip() != "":
            try:
                servicio_oid = ObjectId(reserva.id_servicio)
            except Exception:
                servicio_oid = None

        doc_reserva = {
            "id_barbero": barbero_oid,
            "id_cliente": cliente_oid,
            "id_servicio": servicio_oid,
            "servicio_nombre": reserva.servicio_nombre,
            "fecha": fecha_str,
            "hora": reserva.hora,
            "estado": "pendiente"
        }
        rid = insert_document(reservas_col, doc_reserva)

        barberos_col.update_one(
            {"_id": barbero_oid, "disponibilidades": {"$elemMatch": {"fecha": fecha_str, "hora": reserva.hora}}},
            {"$set": {"disponibilidades.$.estado": "pendiente"}}
        )

        return {"mensaje": "Reserva creada correctamente (pendiente de confirmación)", "id_reserva": str(rid)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.get("/reservas/pendientes/")
def reservas_pendientes():
    return [to_json(r) for r in reservas_col.find({"estado": "pendiente"})]


@app.put("/reservas/confirmar/{id_reserva}")
def confirmar_reserva(id_reserva: str):
    r = update_document(reservas_col, id_reserva, {"estado": "confirmado"})
    if r == 0:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return {"mensaje": "Reserva confirmada correctamente"}


@app.delete("/reservas/cancelar/{id_reserva}")
def cancelar_reserva(id_reserva: str):
    r = delete_document(reservas_col, id_reserva)
    if r == 0:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return {"mensaje": "Reserva cancelada correctamente"}


@app.get("/reservas/detalle/")
def reservas_detalle():
    try:
        reservas = list(reservas_col.aggregate([
            {"$lookup": {"from": "clientes", "localField": "id_cliente", "foreignField": "_id", "as": "cliente"}},
            {"$lookup": {"from": "barberos", "localField": "id_barbero", "foreignField": "_id", "as": "barbero"}},
            {"$lookup": {"from": "servicios", "localField": "id_servicio", "foreignField": "_id", "as": "servicio"}}
        ]))
        return [to_json(r) for r in reservas]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/barbero/agenda/{barbero_id}")
def get_agenda_barbero(barbero_id: str):
    try:
        oid = ObjectId(barbero_id)
        reservas = list(reservas_col.aggregate([
            {"$match": {"id_barbero": oid, "estado": {"$in": ["pendiente", "confirmado", "agendado"]}}},
            {"$lookup": {"from": "clientes", "localField": "id_cliente", "foreignField": "_id", "as": "cliente"}},
            {"$lookup": {"from": "servicios", "localField": "id_servicio", "foreignField": "_id", "as": "servicio"}},
        ]))
        return [to_json(r) for r in reservas]
    except errors.InvalidId:
        raise HTTPException(status_code=400, detail="ID inválido")


@app.get("/barbero/historial/{barbero_id}")
def get_historial_barbero(barbero_id: str):
    try:
        oid = ObjectId(barbero_id)
        query = {"id_barbero": oid, "estado": "completado"}
        return [to_json(cita) for cita in reservas_col.find(query)]
    except errors.InvalidId:
        raise HTTPException(status_code=400, detail="ID inválido")


def regenerar_disponibilidad():
    hoy = datetime.now().date()
    futuro = hoy + timedelta(days=7)
    for barbero in barberos_col.find():
        fechas_existentes = [d["fecha"] for d in barbero.get("disponibilidades", [])]
        nuevas = []
        for i in range(7):
            fecha = (futuro + timedelta(days=i)).isoformat()
            if fecha not in fechas_existentes:
                for hora in ["08:00","09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00"]:
                    nuevas.append({"fecha": fecha, "hora": hora, "estado": "disponible"})
        if nuevas:
            barberos_col.update_one({"_id": barbero["_id"]}, {"$push": {"disponibilidades": {"$each": nuevas}}})


if __name__ == "__main__":
    regenerar_disponibilidad()
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)

