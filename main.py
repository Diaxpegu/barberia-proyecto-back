from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
import os

# Importar colecciones desde database.py
from database import db, clientes_col, barberos_col, servicios_col, productos_col, reservas_col, disponibilidades_col, jefes_col, admin_col
from crud import to_json, insert_document, update_document, delete_document
from schemas import ClienteSchema, BarberoSchema, ServicioSchema, ProductoSchema, DisponibilidadSchema, ReservaSchema
from scheduler import iniciar_scheduler

app = FastAPI(title="API Barbería", version="1.9.0")

# Configuración de CORS
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

# -----------------------
# EVENTOS DE ARRANQUE
# -----------------------
@app.on_event("startup")
def startup_event():
    iniciar_scheduler()

# -----------------------
# MODELOS
# -----------------------
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

# -----------------------
# RUTAS GENERALES
# -----------------------
@app.get("/")
def root():
    return {"mensaje": f"API conectada correctamente a MongoDB (BD {db.name})"}

@app.post("/login/")
def login(datos_login: LoginSchema):
    usuario = datos_login.usuario
    contrasena = datos_login.contrasena

    barbero = barberos_col.find_one({"usuario": usuario})
    if barbero and barbero.get("contrasena") == contrasena:
        return {"usuario": barbero["usuario"], "rol": "barbero", "_id": str(barbero["_id"])}
    
    jefe = jefes_col.find_one({"usuario": usuario})
    if jefe and jefe.get("contrasena") == contrasena:
        return {"usuario": jefe["usuario"], "rol": "jefe", "_id": str(jefe["_id"])}

    raise HTTPException(status_code=404, detail="Usuario o contraseña incorrectos")

# -----------------------
# CLIENTES
# -----------------------
@app.get("/clientes/")
def listar_clientes():
    return [to_json(c) for c in clientes_col.find()]

@app.post("/clientes/")
def crear_cliente(cliente: ClienteSchema):
    if clientes_col.find_one({"correo": cliente.correo}):
        raise HTTPException(status_code=400, detail="El cliente ya existe")
    cid = insert_document(clientes_col, cliente.dict())
    return {"mensaje": "Cliente creado correctamente", "id": str(cid)}

@app.put("/clientes/{cliente_id}")
def actualizar_cliente(cliente_id: str, data: dict = Body(...)):
    modified = update_document(clientes_col, cliente_id, data)
    if modified == 0:
        raise HTTPException(status_code=404, detail="Cliente no encontrado o sin cambios")
    return {"mensaje": "Cliente actualizado correctamente"}

@app.delete("/clientes/{cliente_id}")
def eliminar_cliente(cliente_id: str):
    deleted = delete_document(clientes_col, cliente_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"mensaje": "Cliente eliminado correctamente"}

# -----------------------
# BARBEROS
# -----------------------
@app.get("/barberos/")
def listar_barberos():
    lista = []
    for b in barberos_col.find():
        data = to_json(b)
        data.pop("contrasena", None)
        data["especialidad"] = data.get("especialidad") or "No asignada"
        if isinstance(data.get("disponibilidades"), list):
            data["disponibilidades"] = f"{len(data['disponibilidades'])} horarios"
        lista.append(data)
    return lista

@app.get("/barberos/{barbero_id}")
def obtener_barbero(barbero_id: str):
    b = barberos_col.find_one({"_id": ObjectId(barbero_id)})
    if not b:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")
    data = to_json(b)
    data.pop("contrasena", None)
    data["especialidad"] = data.get("especialidad") or "No asignada"
    return data

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

@app.put("/barberos/{barbero_id}")
def actualizar_barbero(barbero_id: str, data: dict = Body(...)):
    campos = {k: data[k] for k in ["nombre", "especialidad"] if k in data}
    if not campos:
        raise HTTPException(status_code=400, detail="Nada para actualizar")
    modified = update_document(barberos_col, barbero_id, campos)
    if modified == 0:
        raise HTTPException(status_code=404, detail="Barbero no encontrado o sin cambios")
    return {"mensaje": "Perfil actualizado correctamente"}

@app.delete("/barberos/{barbero_id}")
def eliminar_barbero(barbero_id: str):
    deleted = delete_document(barberos_col, barbero_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")
    return {"mensaje": "Barbero eliminado correctamente"}

# -----------------------
# DISPONIBILIDADES POR BARBERO
# -----------------------
@app.get("/barberos/{barbero_id}/disponibilidades")
def obtener_disponibilidades(barbero_id: str):
    barbero = barberos_col.find_one({"_id": ObjectId(barbero_id)})
    if not barbero:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")
    
    # Obtener solo las disponibilidades
    disponibilidades = barbero.get("disponibilidades", [])
    return {"barbero_id": barbero_id, "nombre": barbero["nombre"], "disponibilidades": disponibilidades}


# -----------------------
# RESERVAS
# -----------------------
@app.get("/reservas/")
def listar_reservas():
    return [to_json(r) for r in reservas_col.find()]

@app.post("/reservas/")
def crear_reserva(reserva: ReservaCreate):
    data = reserva.dict()
    rid = insert_document(reservas_col, data)
    return {"mensaje": "Reserva creada correctamente", "id": rid}

@app.put("/reservas/{reserva_id}")
def actualizar_reserva(reserva_id: str, data: dict = Body(...)):
    modified = update_document(reservas_col, reserva_id, data)
    if modified == 0:
        raise HTTPException(status_code=404, detail="Reserva no encontrada o sin cambios")
    return {"mensaje": "Reserva actualizada correctamente"}

@app.delete("/reservas/{reserva_id}")
def eliminar_reserva(reserva_id: str):
    deleted = delete_document(reservas_col, reserva_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return {"mensaje": "Reserva eliminada correctamente"}

# -----------------------
# Función para regenerar disponibilidad semanal
# -----------------------
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

# -----------------------
# RUN SERVER
# -----------------------
if __name__ == "__main__":
    regenerar_disponibilidad()
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)


