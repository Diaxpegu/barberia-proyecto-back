from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId
from datetime import datetime, timedelta
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

app = FastAPI(title="API Barbería", version="1.3.0")

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
    clientes = list(clientes_col.find({}, {"_id": 0}))
    return clientes

@app.get("/barberos/")
def listar_barberos():
    barberos_lista = []
    for b in barberos_col.find():
        data = to_json(b)
        d = data.get("disponibilidades")
        if isinstance(d, list):
            data["disponibilidades"] = f"{len(d)} horarios definidos" if d else "Sin horarios"
        else:
            data["disponibilidades"] = "No definido"
        if not data.get("especialidad"):
            data["especialidad"] = "No asignada"
        data.pop("contrasena", None)
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
    if not data.get("especialidad"):
        data["especialidad"] = "No asignada"
    return data

@app.get("/barberos/{barbero_id}/disponibilidades")
def disponibilidades_por_barbero(barbero_id: str):
    try:
        b = barberos_col.find_one({"_id": ObjectId(barbero_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    if not b:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")
    disponibles = []
    for d in b.get("disponibilidades", []):
        if d.get("estado") == "disponible":
            disponibles.append({"fecha": d.get("fecha"), "hora": d.get("hora"), "estado": "disponible"})
    return disponibles

@app.post("/barberos/")
def crear_barbero(barbero: BarberoSchema):
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
    if barberos_col.find_one({"usuario": barbero.usuario}):
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    bid = insert_document(barberos_col, nuevo)
    return {"mensaje": "Barbero creado correctamente", "id": str(bid)}

@app.delete("/barberos/{barbero_id}")
def eliminar_barbero(barbero_id: str):
    try:
        r = barberos_col.delete_one({"_id": ObjectId(barbero_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")
    return {"mensaje": "Barbero eliminado correctamente"}

@app.get("/servicios/")
def listar_servicios():
    return [to_json(s) for s in servicios_col.find()]

@app.get("/productos/")
def listar_productos():
    return [to_json(p) for p in productos_col.find()]

@app.get("/disponibilidad/libre/")
def disponibilidad_libre(id_barbero: str = None):
    if id_barbero:
        try:
            b = barberos_col.find_one({"_id": ObjectId(id_barbero)})
        except Exception:
            raise HTTPException(status_code=400, detail="ID inválido")
        if not b:
            raise HTTPException(status_code=404, detail="Barbero no encontrado")
        disponibles = []
        for d in b.get("disponibilidades", []):
            if d.get("estado") == "disponible":
                disponibles.append({"fecha": d.get("fecha"), "hora": d.get("hora"), "estado": "disponible"})
        return disponibles

    disponibles = []
    for b in barberos_col.find():
        for d in b.get("disponibilidades", []):
            if d.get("estado") == "disponible":
                disponibles.append({
                    "_id": str(b["_id"]),
                    "nombre": b.get("nombre"),
                    "especialidad": b.get("especialidad", ""),
                    "fecha": d.get("fecha"),
                    "hora": d.get("hora"),
                    "estado": "disponible"
                })
    return disponibles

@app.put("/disponibilidad/bloquear/{barbero_id}/{fecha}/{hora}")
def bloquear_disponibilidad(barbero_id: str, fecha: str, hora: str):
    try:
        r = barberos_col.update_one(
            {"_id": ObjectId(barbero_id), "disponibilidades": {"$elemMatch": {"fecha": fecha, "hora": hora}}},
            {"$set": {"disponibilidades.$.estado": "bloqueado"}}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Error al bloquear disponibilidad")
    if r.modified_count == 0:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")
    return {"mensaje": "Horario bloqueado correctamente"}

@app.post("/login/")
def login(datos_login: LoginSchema):
    barbero = barberos_col.find_one({"usuario": datos_login.usuario})
    if barbero and barbero["contrasena"] == datos_login.contrasena:
        return {
            "usuario": barbero["usuario"], 
            "rol": "barbero",
            "_id": str(barbero["_id"])
        }

    jefe = jefes_col.find_one({"usuario": datos_login.usuario})
    if jefe and jefe["contrasena"] == datos_login.contrasena:
        return {
            "usuario": jefe["usuario"], 
            "rol": "jefe",
            "_id": str(jefe["_id"])
        }

    raise HTTPException(status_code=404, detail="Usuario o contraseña incorrectos")

@app.get("/barbero/agenda/{barbero_id}")
def get_agenda_barbero(barbero_id: str):
    """Obtiene la agenda (citas pendientes/confirmadas) de un barbero."""
    try:

        oid = ObjectId(barbero_id) 

        query = {
            "id_barbero": oid, 
            "estado": {"$in": ["pendiente", "confirmado", "agendado"]}
        }
        agenda = list(reservas_col.find(query))
        return [to_json(cita) for cita in agenda]
    except errors.InvalidId:
        raise HTTPException(status_code=400, detail="ID de barbero inválido")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/barbero/historial/{barbero_id}")
def get_historial_barbero(barbero_id: str):
    """Obtiene el historial (citas completadas) de un barbero."""
    try:
        oid = ObjectId(barbero_id)
        query = {"id_barbero": oid, "estado": "completado"}
        historial = list(reservas_col.find(query))

        return [to_json(cita) for cita in historial]
    except errors.InvalidId:
        raise HTTPException(status_code=400, detail="ID de barbero inválido")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            barberos_col.update_one(
                {"_id": barbero["_id"]},
                {"$push": {"disponibilidades": {"$each": nuevas}}}
            )

if __name__ == "__main__":
    regenerar_disponibilidad()
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)