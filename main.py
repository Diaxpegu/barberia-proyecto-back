from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId, errors
from datetime import datetime, timedelta, date
from pydantic import BaseModel
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

app = FastAPI(title="API Barbería", version="1.7.0")


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

class LoginSchema(BaseModel):
    usuario: str
    contrasena: str


@app.get("/")
def root():
    return {"mensaje": "API conectada correctamente a MongoDB (BD test)"}



@app.get("/clientes/")
def listar_clientes():
    return [to_json(c) for c in clientes_col.find()]


@app.post("/clientes/")
def crear_cliente(cliente: ClienteSchema):
    """Crea o devuelve un cliente ya existente."""
    existente = clientes_col.find_one({"correo": cliente.correo})
    if existente:
        return {"mensaje": "Cliente ya registrado", "id": str(existente["_id"])}
    cid = insert_document(clientes_col, cliente.dict())
    return {"mensaje": "Cliente agregado correctamente", "id": cid}



@app.get("/barberos/")
def listar_barberos():
    barberos_lista = []
    for b in barberos_col.find():
        data = to_json(b)
        data.pop("contrasena", None)
        data["especialidad"] = data.get("especialidad") or "No asignada"
        data["disponibilidades"] = (
            f"{len(data.get('disponibilidades', []))} horarios definidos"
            if isinstance(data.get("disponibilidades"), list)
            else "No definido"
        )
        barberos_lista.append(data)
    return barberos_lista


@app.get("/barberos/{barbero_id}")
def obtener_barbero(barbero_id: str):
    """Obtiene datos individuales del barbero (para su panel o reservas)."""
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


@app.get("/barberos/{barbero_id}/disponibilidades")
def disponibilidades_por_barbero(barbero_id: str):
    """Lista las horas disponibles de un barbero específico."""
    try:
        b = barberos_col.find_one({"_id": ObjectId(barbero_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    if not b:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")

    return [d for d in b.get("disponibilidades", []) if d.get("estado") == "disponible"]


@app.post("/barberos/")
def crear_barbero(barbero: BarberoSchema):
    """Crea un nuevo barbero con disponibilidad automática de 7 días."""
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


@app.put("/disponibilidad/bloquear/{barbero_id}/{fecha}/{hora}")
def bloquear_disponibilidad(barbero_id: str, fecha: str, hora: str):
    """Bloquea una hora específica del barbero."""
    r = barberos_col.update_one(
        {"_id": ObjectId(barbero_id), "disponibilidades": {"$elemMatch": {"fecha": fecha, "hora": hora}}},
        {"$set": {"disponibilidades.$.estado": "ocupado"}}
    )
    if r.modified_count == 0:
        raise HTTPException(status_code=404, detail="No se encontró esa hora disponible")
    return {"mensaje": "Horario bloqueado correctamente"}



@app.get("/servicios/")
def listar_servicios():
    return [to_json(s) for s in servicios_col.find()]


@app.get("/productos/")
def listar_productos():
    return [to_json(p) for p in productos_col.find()]



@app.post("/login/")
def login(datos_login: LoginSchema):
    """Valida si es barbero o jefe (admin)."""
    barbero = barberos_col.find_one({"usuario": datos_login.usuario})
    if barbero and barbero["contrasena"] == datos_login.contrasena:
        return {"usuario": barbero["usuario"], "rol": "barbero", "_id": str(barbero["_id"])}

    jefe = jefes_col.find_one({"usuario": datos_login.usuario})
    if jefe and jefe["contrasena"] == datos_login.contrasena:
        return {"usuario": jefe["usuario"], "rol": "jefe", "_id": str(jefe["_id"])}

    raise HTTPException(status_code=404, detail="Usuario o contraseña incorrectos")



@app.post("/reservas/")
def crear_reserva(reserva: ReservaSchema):
    """Crea una reserva y, si el cliente no existe, lo registra automáticamente."""
    try:

        cliente_data = {
            "nombre": reserva.nombre_cliente,
            "correo": reserva.correo_cliente,
            "telefono": reserva.telefono_cliente,
        }
        existente = clientes_col.find_one({"correo": reserva.correo_cliente})
        if existente:
            cliente_oid = existente["_id"]
        else:
            cliente_oid = ObjectId(insert_document(clientes_col, cliente_data))


        barbero_oid = ObjectId(reserva.id_barbero)
        datos_reserva = reserva.dict()
        datos_reserva["id_barbero"] = barbero_oid
        datos_reserva["id_cliente"] = cliente_oid
        datos_reserva["fecha"] = str(reserva.fecha)

        reserva_id = insert_document(reservas_col, datos_reserva)


        barberos_col.update_one(
            {"_id": barbero_oid, "disponibilidades": {"$elemMatch": {"fecha": str(reserva.fecha), "hora": reserva.hora}}},
            {"$set": {"disponibilidades.$.estado": "ocupado"}}
        )

        return {"mensaje": "Reserva creada exitosamente", "id_reserva": str(reserva_id)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear reserva: {str(e)}")


@app.get("/reservas/pendientes/")
def reservas_pendientes():
    return [to_json(r) for r in reservas_col.find({"estado": "pendiente"})]


@app.get("/reservas/detalle/")
def reservas_detalle():
    """Devuelve reservas con información completa (cliente, barbero y servicio)."""
    try:
        reservas = list(reservas_col.aggregate([
            {"$lookup": {"from": "clientes", "localField": "id_cliente", "foreignField": "_id", "as": "cliente"}},
            {"$lookup": {"from": "barberos", "localField": "id_barbero", "foreignField": "_id", "as": "barbero"}},
            {"$lookup": {"from": "servicios", "localField": "id_servicio", "foreignField": "_id", "as": "servicio"}}
        ]))
        return [to_json(r) for r in reservas]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/reservas/confirmar/{id_reserva}")
def confirmar_reserva(id_reserva: str):
    modified = update_document(reservas_col, id_reserva, {"estado": "confirmado"})
    if modified == 0:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return {"mensaje": "Reserva confirmada correctamente"}


@app.delete("/reservas/cancelar/{id_reserva}")
def cancelar_reserva(id_reserva: str):
    deleted = delete_document(reservas_col, id_reserva)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return {"mensaje": "Reserva cancelada correctamente"}

@app.get("/barbero/agenda/{barbero_id}")
def get_agenda_barbero(barbero_id: str):
    oid = ObjectId(barbero_id)
    query = {"id_barbero": oid, "estado": {"$in": ["pendiente", "confirmado"]}}
    return [to_json(cita) for cita in reservas_col.find(query)]


@app.get("/barbero/historial/{barbero_id}")
def get_historial_barbero(barbero_id: str):
    oid = ObjectId(barbero_id)
    query = {"id_barbero": oid, "estado": "completado"}
    return [to_json(cita) for cita in reservas_col.find(query)]


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
