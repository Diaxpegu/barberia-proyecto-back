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
# CRUD Mongo
from crud import to_json, insert_document, update_document, delete_document
from scheduler import iniciar_scheduler
from schemas import BarberoSchema

app = FastAPI(title="API Barbería Híbrida", version="2.2.0")

# -----------------------
# CORS (SOLUCIÓN DEFINITIVA)
# -----------------------
origins = ["*"] # Permitir todo para que no falle la conexión del Front
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
# MODELOS DE DATOS
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
    # Datos del cliente (vienen del formulario)
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
# LOGIN (RESTABLECIDO A MONGODB)
# ==========================================
@app.post("/login/")
def login(datos_login: LoginSchema):
    usuario, contrasena = datos_login.usuario, datos_login.contrasena
    
    # 1. Buscar en Barberos (Mongo)
    barbero = barberos_col.find_one({"usuario": usuario})
    if barbero and barbero.get("contrasena") == contrasena:
        return {"usuario": barbero["usuario"], "rol": "barbero", "_id": str(barbero["_id"])}
    
    # 2. Buscar en Jefes (Mongo)
    jefe = jefes_col.find_one({"usuario": usuario})
    if jefe and jefe.get("contrasena") == contrasena:
        return {"usuario": jefe["usuario"], "rol": "jefe", "_id": str(jefe["_id"])}

    raise HTTPException(status_code=404, detail="Usuario o contraseña incorrectos")

# Endpoint para crear jefe manualmente en MONGO (para poder entrar al panel)
@app.post("/crear-jefe-mongo/")
def crear_jefe(usuario: str, contrasena: str):
    if jefes_col.find_one({"usuario": usuario}):
        return {"mensaje": "Jefe ya existe"}
    jefes_col.insert_one({"usuario": usuario, "contrasena": contrasena})
    return {"mensaje": "Jefe creado en Mongo"}

# ==========================================
# CLIENTES (AHORA EN MYSQL)
# ==========================================
@app.get("/clientes/")
def listar_clientes(db_sql: Session = Depends(get_db_sql)):
    clientes = db_sql.query(ClienteSQL).all()
    return clientes

@app.post("/clientes/")
def crear_cliente(cliente: ClienteSchema, db_sql: Session = Depends(get_db_sql)):
    existe = db_sql.query(ClienteSQL).filter(ClienteSQL.correo == cliente.correo).first()
    if existe:
        raise HTTPException(status_code=400, detail="El cliente ya existe (correo duplicado)")
    
    nuevo_cliente = ClienteSQL(
        nombre=cliente.nombre,
        apellido=cliente.apellido,
        correo=cliente.correo,
        telefono=cliente.telefono,
        rut=cliente.rut,
        direccion=cliente.direccion,
        estado="nuevo"
    )
    db_sql.add(nuevo_cliente)
    db_sql.commit()
    db_sql.refresh(nuevo_cliente)
    return {"mensaje": "Cliente creado en MySQL", "id": nuevo_cliente.id}

@app.put("/clientes/{cliente_id}")
def actualizar_cliente(cliente_id: int, data: dict = Body(...), db_sql: Session = Depends(get_db_sql)):
    cliente = db_sql.query(ClienteSQL).filter(ClienteSQL.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    for key, value in data.items():
        if hasattr(cliente, key):
            setattr(cliente, key, value)
    
    db_sql.commit()
    return {"mensaje": "Cliente actualizado en MySQL"}

@app.delete("/clientes/{cliente_id}")
def eliminar_cliente(cliente_id: int, db_sql: Session = Depends(get_db_sql)):
    cliente = db_sql.query(ClienteSQL).filter(ClienteSQL.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    db_sql.delete(cliente)
    db_sql.commit()
    return {"mensaje": "Cliente eliminado de MySQL"}

# ==========================================
# RESERVAS (MONGODB + MYSQL LINK)
# ==========================================
@app.post("/reservas/")
def crear_reserva(reserva: ReservaCreate, db_sql: Session = Depends(get_db_sql)):
    try:
        # 1. GESTIÓN DEL CLIENTE EN MYSQL
        mysql_client_id = None
        correo = reserva.email_cliente.strip() if reserva.email_cliente else None
        
        if correo:
            # Buscar cliente en SQL
            cliente_sql = db_sql.query(ClienteSQL).filter(ClienteSQL.correo == correo).first()
            
            if cliente_sql:
                mysql_client_id = cliente_sql.id
                # Actualizar datos si es necesario (opcional)
                cliente_sql.telefono = reserva.telefono_cliente
                db_sql.commit()
            else:
                # Crear cliente nuevo en SQL
                nuevo_cliente = ClienteSQL(
                    nombre=reserva.nombre_cliente,
                    apellido=reserva.apellido_cliente,
                    correo=correo,
                    telefono=reserva.telefono_cliente,
                    rut=reserva.rut_cliente,
                    estado="con_reserva"
                )
                db_sql.add(nuevo_cliente)
                db_sql.commit()
                db_sql.refresh(nuevo_cliente)
                mysql_client_id = nuevo_cliente.id
        else:
            raise HTTPException(status_code=400, detail="Se requiere email del cliente")

        # 2. GESTIÓN DE LA RESERVA EN MONGO
        barbero_oid = ObjectId(reserva.id_barbero)
        fecha_str = str(reserva.fecha)
        
        servicio_oid = None
        if reserva.id_servicio:
             try: servicio_oid = ObjectId(reserva.id_servicio)
             except: pass
        
        doc_reserva = {
            "id_barbero": barbero_oid,
            "id_cliente_mysql": mysql_client_id, # Guardamos la referencia a SQL
            "id_servicio": servicio_oid,
            "servicio_nombre": reserva.servicio_nombre,
            "fecha": fecha_str,
            "hora": reserva.hora,
            "estado": "pendiente",
            # Snapshot de datos para visualización rápida sin hacer query a SQL siempre
            "datos_cliente_snapshot": { 
                "nombre": f"{reserva.nombre_cliente} {reserva.apellido_cliente or ''}",
                "correo": correo,
                "telefono": reserva.telefono_cliente
            }
        }
        rid = insert_document(reservas_col, doc_reserva)

        # 3. ACTUALIZAR DISPONIBILIDAD BARBERO (MONGO)
        barberos_col.update_one(
            {"_id": barbero_oid, "disponibilidades": {"$elemMatch": {"fecha": fecha_str, "hora": reserva.hora}}},
            {"$set": {"disponibilidades.$.estado": "pendiente"}}
        )

        return {"mensaje": "Reserva creada correctamente", "id_reserva": str(rid)}

    except Exception as e:
        print(f"Error reserva: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/reservas/detalle/")
def listar_reservas_detalle(db_sql: Session = Depends(get_db_sql)):
    # Traemos reservas de Mongo
    reservas_mongo = list(reservas_col.find())
    resultado = []
    
    for r in reservas_mongo:
        r_json = to_json(r)
        
        # JOIN MANUAL: Traer datos frescos de MySQL si existe el ID
        if "id_cliente_mysql" in r and r["id_cliente_mysql"]:
            cliente_sql = db_sql.query(ClienteSQL).filter(ClienteSQL.id == r["id_cliente_mysql"]).first()
            if cliente_sql:
                r_json["cliente"] = [{
                    "nombre": f"{cliente_sql.nombre} {cliente_sql.apellido or ''}",
                    "correo": cliente_sql.correo,
                    "telefono": cliente_sql.telefono,
                    "estado_cliente": cliente_sql.estado
                }]
            else:
                # Si se borró de SQL, usamos el snapshot
                snap = r.get("datos_cliente_snapshot", {})
                r_json["cliente"] = [{"nombre": snap.get("nombre", "Desconocido") + " (Eliminado SQL)"}]
        else:
             snap = r.get("datos_cliente_snapshot", {})
             r_json["cliente"] = [{"nombre": snap.get("nombre", "Cliente")}]

        # Lookup barbero (Mongo)
        if "id_barbero" in r:
             try:
                b = barberos_col.find_one({"_id": ObjectId(r["id_barbero"])})
                if b: r_json["barbero"] = [{"nombre": b.get("nombre")}]
             except: pass

        resultado.append(r_json)
        
    return resultado

@app.put("/reservas/actualizar/{reserva_id}")
def actualizar_reserva(reserva_id: str, data: dict = Body(...), db_sql: Session = Depends(get_db_sql)):
    # 1. Actualizar Mongo
    modified = update_document(reservas_col, reserva_id, data)
    
    # 2. CASCADA: Actualizar estado en MySQL
    if "estado" in data:
        nuevo_estado = data["estado"]
        reserva = reservas_col.find_one({"_id": ObjectId(reserva_id)})
        
        if reserva and "id_cliente_mysql" in reserva:
            cliente_id = reserva["id_cliente_mysql"]
            cliente_sql = db_sql.query(ClienteSQL).filter(ClienteSQL.id == cliente_id).first()
            
            if cliente_sql:
                if nuevo_estado in ["completado", "realizado", "listo"]:
                    cliente_sql.estado = "atendido"
                elif nuevo_estado == "cancelado":
                    cliente_sql.estado = "cancelado"
                
                db_sql.commit()

    return {"mensaje": "Reserva y estado de cliente actualizados"}

@app.delete("/reservas/cancelar/{reserva_id}")
def eliminar_reserva(reserva_id: str):
    deleted = delete_document(reservas_col, reserva_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return {"mensaje": "Reserva eliminada"}

# ==========================================
# BARBEROS (MONGO - RESTABLECIDO)
# ==========================================
@app.get("/barberos/")
def listar_barberos():
    lista = []
    # IMPORTANTE: Esto debe funcionar para que el front cargue
    if barberos_col is not None:
        for b in barberos_col.find():
            data = to_json(b)
            data.pop("contrasena", None)
            data["especialidad"] = data.get("especialidad") or "No asignada"
            data["disponibilidades"] = data.get("disponibilidades", [])
            lista.append(data)
    return lista

@app.get("/barberos/{barbero_id}")
def obtener_barbero(barbero_id: str):
    try:
        b = barberos_col.find_one({"_id": ObjectId(barbero_id)})
        if not b:
            raise HTTPException(status_code=404, detail="Barbero no encontrado")
        data = to_json(b)
        data.pop("contrasena", None)
        return data
    except:
        raise HTTPException(status_code=404, detail="ID inválido o no encontrado")

@app.post("/barberos/")
def crear_barbero(barbero: BarberoSchema):
    if barberos_col.find_one({"usuario": barbero.usuario}):
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    
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
    return {"mensaje": "Barbero creado en Mongo", "id": str(bid)}

@app.get("/barberos/{barbero_id}/disponibilidades")
def obtener_disponibilidades(barbero_id: str):
    try:
        b = barberos_col.find_one({"_id": ObjectId(barbero_id)})
        if not b: raise HTTPException(status_code=404)
        return [{"fecha": d["fecha"], "hora": d["hora"], "estado": d["estado"]} for d in b.get("disponibilidades", [])]
    except:
        return []

@app.put("/disponibilidad/bloquear/{barbero_id}/{fecha}/{hora}")
def bloquear_disponibilidad(barbero_id: str, fecha: str, hora: str):
    barberos_col.update_one(
        {"_id": ObjectId(barbero_id), "disponibilidades": {"$elemMatch": {"fecha": fecha, "hora": hora}}},
        {"$set": {"disponibilidades.$.estado": "ocupado"}}
    )
    return {"mensaje": "Bloqueado"}

# ==========================================
# RESTO DE ENDPOINTS (SERVICIOS, ETC)
# ==========================================
@app.get("/servicios/")
def listar_servicios():
    return [to_json(s) for s in servicios_col.find()]

@app.get("/barbero/agenda/{barbero_id}")
def get_agenda(barbero_id: str):
    try:
        oid = ObjectId(barbero_id)
        # Buscar reservas en Mongo para este barbero
        reservas = list(reservas_col.aggregate([
            {"$match": {"id_barbero": oid, "estado": {"$in": ["pendiente", "confirmado", "agendado"]}}},
            # No hacemos lookup automatico complejo para evitar errores si no hay ids, 
            # pero devolvemos los datos básicos
        ]))
        
        # Procesar para el front
        resultado = []
        for r in reservas:
            rj = to_json(r)
            snap = r.get("datos_cliente_snapshot", {})
            rj["cliente"] = [{"nombre": snap.get("nombre", "Cliente")}]
            rj["servicio"] = [{"nombre_servicio": r.get("servicio_nombre", "Servicio")}]
            resultado.append(rj)
            
        return resultado
    except Exception as e:
        print(e)
        return []

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)