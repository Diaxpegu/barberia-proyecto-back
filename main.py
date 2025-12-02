from fastapi import FastAPI, HTTPException, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId, errors
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
import os

# SQL Imports
from sqlalchemy.orm import Session
from database import (
    db, barberos_col, servicios_col, productos_col, reservas_col, jefes_col,
    get_db_sql, ClienteSQL
)
from crud import to_json, insert_document, update_document, delete_document
from scheduler import iniciar_scheduler
from schemas import BarberoSchema

app = FastAPI(title="API Barbería Híbrida", version="2.2.0")

# CORS: Permitir todo para evitar bloqueos
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    iniciar_scheduler()

# -----------------------
# MODELOS
# -----------------------
class LoginSchema(BaseModel):
    usuario: str
    contrasena: str

class ClienteSchema(BaseModel):
    nombre: str
    apellido: Optional[str] = None
    correo: str
    telefono: str
    rut: Optional[str] = None
    direccion: Optional[str] = None

class ReservaCreate(BaseModel):
    id_barbero: str
    fecha: str
    hora: str
    id_servicio: Optional[str] = None
    nombre_cliente: Optional[str] = None
    apellido_cliente: Optional[str] = None
    email_cliente: Optional[str] = None
    telefono_cliente: Optional[str] = None
    rut_cliente: Optional[str] = None
    servicio_nombre: Optional[str] = None

@app.get("/")
def root():
    return {"mensaje": "API Híbrida Activa: Clientes SQL, resto MongoDB"}

# ==========================================
# LOGIN (MONGODB)
# ==========================================
@app.post("/login/")
def login(datos_login: LoginSchema):
    usuario, contrasena = datos_login.usuario, datos_login.contrasena
    
    # 1. Barberos
    barbero = barberos_col.find_one({"usuario": usuario})
    if barbero and barbero.get("contrasena") == contrasena:
        return {"usuario": barbero["usuario"], "rol": "barbero", "_id": str(barbero["_id"])}
    
    # 2. Jefes
    jefe = jefes_col.find_one({"usuario": usuario})
    if jefe and jefe.get("contrasena") == contrasena:
        return {"usuario": jefe["usuario"], "rol": "jefe", "_id": str(jefe["_id"])}

    raise HTTPException(status_code=404, detail="Usuario o contraseña incorrectos")

# ==========================================
# CLIENTES (MYSQL)
# ==========================================
@app.get("/clientes/")
def listar_clientes(db_sql: Session = Depends(get_db_sql)):
    return db_sql.query(ClienteSQL).all()

@app.post("/clientes/")
def crear_cliente(cliente: ClienteSchema, db_sql: Session = Depends(get_db_sql)):
    if db_sql.query(ClienteSQL).filter(ClienteSQL.correo == cliente.correo).first():
        raise HTTPException(status_code=400, detail="Cliente ya existe")
    
    nuevo = ClienteSQL(
        nombre=cliente.nombre,
        apellido=cliente.apellido,
        correo=cliente.correo,
        telefono=cliente.telefono,
        rut=cliente.rut,
        direccion=cliente.direccion,
        estado="nuevo"
    )
    db_sql.add(nuevo)
    db_sql.commit()
    db_sql.refresh(nuevo)
    return {"mensaje": "Cliente creado en MySQL", "id": nuevo.id}

@app.put("/clientes/{cliente_id}")
def actualizar_cliente(cliente_id: int, data: dict = Body(...), db_sql: Session = Depends(get_db_sql)):
    cliente = db_sql.query(ClienteSQL).filter(ClienteSQL.id == cliente_id).first()
    if not cliente: raise HTTPException(status_code=404, detail="No encontrado")
    
    for k, v in data.items():
        if hasattr(cliente, k): setattr(cliente, k, v)
    
    db_sql.commit()
    return {"mensaje": "Actualizado"}

@app.delete("/clientes/{cliente_id}")
def eliminar_cliente(cliente_id: int, db_sql: Session = Depends(get_db_sql)):
    cliente = db_sql.query(ClienteSQL).filter(ClienteSQL.id == cliente_id).first()
    if not cliente: raise HTTPException(status_code=404, detail="No encontrado")
    db_sql.delete(cliente)
    db_sql.commit()
    return {"mensaje": "Eliminado"}

# ==========================================
# RESERVAS (MONGODB + MYSQL LINK)
# ==========================================
@app.post("/reservas/")
def crear_reserva(reserva: ReservaCreate, db_sql: Session = Depends(get_db_sql)):
    try:
        # 1. Gestionar Cliente en MySQL
        mysql_id = None
        if reserva.email_cliente:
            cliente = db_sql.query(ClienteSQL).filter(ClienteSQL.correo == reserva.email_cliente).first()
            if cliente:
                mysql_id = cliente.id
                # Actualizar teléfono si cambió
                if reserva.telefono_cliente:
                    cliente.telefono = reserva.telefono_cliente
                    db_sql.commit()
            else:
                nuevo = ClienteSQL(
                    nombre=reserva.nombre_cliente,
                    apellido=reserva.apellido_cliente,
                    correo=reserva.email_cliente,
                    telefono=reserva.telefono_cliente,
                    rut=reserva.rut_cliente,
                    estado="con_reserva"
                )
                db_sql.add(nuevo)
                db_sql.commit()
                db_sql.refresh(nuevo)
                mysql_id = nuevo.id
        
        # 2. Crear Reserva en Mongo
        doc = {
            "id_barbero": ObjectId(reserva.id_barbero),
            "id_cliente_mysql": mysql_id,
            "id_servicio": ObjectId(reserva.id_servicio) if reserva.id_servicio else None,
            "servicio_nombre": reserva.servicio_nombre,
            "fecha": reserva.fecha,
            "hora": reserva.hora,
            "estado": "pendiente",
            "datos_cliente_snapshot": { # Para visualización rápida
                "nombre": f"{reserva.nombre_cliente} {reserva.apellido_cliente or ''}",
                "correo": reserva.email_cliente
            }
        }
        rid = insert_document(reservas_col, doc)

        # 3. Bloquear horario (Pendiente)
        barberos_col.update_one(
            {"_id": ObjectId(reserva.id_barbero), "disponibilidades": {"$elemMatch": {"fecha": reserva.fecha, "hora": reserva.hora}}},
            {"$set": {"disponibilidades.$.estado": "pendiente"}}
        )

        return {"mensaje": "Reserva creada", "id_reserva": str(rid)}
    except Exception as e:
        print(f"Error reserva: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reservas/detalle/")
def listar_reservas_detalle(db_sql: Session = Depends(get_db_sql)):
    reservas = list(reservas_col.find())
    resultado = []
    for r in reservas:
        rj = to_json(r)
        # Join Manual con MySQL
        if r.get("id_cliente_mysql"):
            c = db_sql.query(ClienteSQL).filter(ClienteSQL.id == r["id_cliente_mysql"]).first()
            if c:
                rj["cliente"] = [{"nombre": f"{c.nombre} {c.apellido or ''}", "correo": c.correo, "telefono": c.telefono}]
            else:
                rj["cliente"] = [{"nombre": "Cliente no encontrado en SQL"}]
        else:
            snap = r.get("datos_cliente_snapshot", {})
            rj["cliente"] = [{"nombre": snap.get("nombre", "Sin nombre")}]
        
        # Join Mongo Barbero/Servicio
        if "id_barbero" in r:
            b = barberos_col.find_one({"_id": ObjectId(r["id_barbero"])})
            if b: rj["barbero"] = [{"nombre": b.get("nombre")}]
        
        if "id_servicio" in r and r["id_servicio"]:
             s = servicios_col.find_one({"_id": ObjectId(r["id_servicio"])})
             if s: rj["servicio"] = [{"nombre_servicio": s.get("nombre_servicio")}]
        else:
             rj["servicio"] = [{"nombre_servicio": r.get("servicio_nombre")}]

        resultado.append(rj)
    return resultado

@app.put("/reservas/actualizar/{reserva_id}")
def actualizar_reserva(reserva_id: str, data: dict = Body(...), db_sql: Session = Depends(get_db_sql)):
    update_document(reservas_col, reserva_id, data)
    
    # Actualizar estado cliente en SQL
    if "estado" in data:
        r = reservas_col.find_one({"_id": ObjectId(reserva_id)})
        if r and r.get("id_cliente_mysql"):
            c = db_sql.query(ClienteSQL).filter(ClienteSQL.id == r["id_cliente_mysql"]).first()
            if c:
                if data["estado"] in ["realizado", "completado"]:
                    c.estado = "atendido"
                elif data["estado"] == "cancelado":
                    c.estado = "cancelado"
                db_sql.commit()
    return {"mensaje": "Actualizado"}

@app.delete("/reservas/cancelar/{reserva_id}")
def eliminar_reserva(reserva_id: str):
    delete_document(reservas_col, reserva_id)
    return {"mensaje": "Eliminada"}

# ==========================================
# BARBEROS (MONGO) - ¡CRUCIAL PARA EL FRONT!
# ==========================================
@app.get("/barberos/")
def listar_barberos():
    # Este endpoint es el que usa tu home page
    lista = []
    for b in barberos_col.find():
        data = to_json(b)
        data.pop("contrasena", None)
        data["especialidad"] = data.get("especialidad") or "No asignada"
        data["disponibilidades"] = data.get("disponibilidades", [])
        lista.append(data)
    return lista

@app.get("/barberos/{barbero_id}")
def obtener_barbero(barbero_id: str):
    b = barberos_col.find_one({"_id": ObjectId(barbero_id)})
    if not b: raise HTTPException(status_code=404)
    data = to_json(b)
    data.pop("contrasena", None)
    return data

@app.post("/barberos/")
def crear_barbero(barbero: BarberoSchema):
    if barberos_col.find_one({"usuario": barbero.usuario}):
        raise HTTPException(status_code=400, detail="Usuario existe")
    
    hoy = datetime.now().date()
    disponibilidades = [
        {"fecha": (hoy + timedelta(days=i)).isoformat(), "hora": h, "estado": "disponible"}
        for i in range(7) for h in ["08:00","09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00"]
    ]
    nuevo = {
        "nombre": barbero.nombre,
        "usuario": barbero.usuario,
        "contrasena": barbero.contrasena,
        "especialidad": barbero.especialidad,
        "disponibilidades": disponibilidades
    }
    bid = insert_document(barberos_col, nuevo)
    return {"mensaje": "Barbero creado", "id": str(bid)}

@app.get("/barberos/{barbero_id}/disponibilidades")
def obtener_disponibilidades(barbero_id: str):
    b = barberos_col.find_one({"_id": ObjectId(barbero_id)})
    if not b: return []
    return b.get("disponibilidades", [])

@app.put("/disponibilidad/bloquear/{barbero_id}/{fecha}/{hora}")
def bloquear_disponibilidad(barbero_id: str, fecha: str, hora: str):
    barberos_col.update_one(
        {"_id": ObjectId(barbero_id), "disponibilidades": {"$elemMatch": {"fecha": fecha, "hora": hora}}},
        {"$set": {"disponibilidades.$.estado": "ocupado"}}
    )
    return {"mensaje": "Bloqueado"}

# ==========================================
# OTROS ENDPOINTS (MONGO)
# ==========================================
@app.get("/servicios/")
def listar_servicios():
    return [to_json(s) for s in servicios_col.find()]

@app.post("/servicios/")
def crear_servicio(s: dict = Body(...)):
    sid = insert_document(servicios_col, s)
    return {"mensaje": "Servicio creado", "id": sid}

@app.delete("/servicios/{sid}")
def eliminar_servicio(sid: str):
    delete_document(servicios_col, sid)
    return {"mensaje": "Eliminado"}

@app.get("/productos/")
def listar_productos():
    return [to_json(p) for p in productos_col.find()]

@app.post("/productos/")
def crear_producto(p: dict = Body(...)):
    pid = insert_document(productos_col, p)
    return {"mensaje": "Producto creado", "id": pid}

@app.get("/barbero/agenda/{barbero_id}")
def get_agenda(barbero_id: str):
    try:
        oid = ObjectId(barbero_id)
        # Buscar reservas
        reservas = list(reservas_col.find({"id_barbero": oid, "estado": {"$in": ["pendiente", "confirmado"]}}))
        res = []
        for r in reservas:
            rj = to_json(r)
            # Simplificado: enviamos nombre del snapshot para el panel del barbero
            snap = r.get("datos_cliente_snapshot", {})
            rj["cliente"] = [{"nombre": snap.get("nombre", "Cliente")}]
            rj["servicio"] = [{"nombre_servicio": r.get("servicio_nombre", "Servicio")}]
            res.append(rj)
        return res
    except: return []

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)