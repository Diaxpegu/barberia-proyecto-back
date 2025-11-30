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
    db, clientes_col, barberos_col, servicios_col, productos_col, reservas_col, 
    get_db_sql, UsuarioSQL
)
from crud import to_json, insert_document, update_document, delete_document

# Scheduler
from scheduler import iniciar_scheduler
# Schemas
from schemas import BarberoSchema

app = FastAPI(title="API Barbería Híbrida", version="2.0.0")

# -----------------------
# CORS (Permisos de acceso)
# -----------------------
origins = [
    # Producción Frontend
    "https://barberia-proyecto-front-production-3f2e.up.railway.app",
    # Producción Backend (por si acaso)
    "https://barberia-proyecto-back-production-f876.up.railway.app",
    # Desarrollo Local (Esto permite probar desde tu PC sin subir cambios, no guarda datos en tu PC)
    "http://localhost:3000"
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
# MODELOS DE DATOS (Pydantic)
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
    return {"mensaje": "API Híbrida Funcionando (Mongo + MySQL Railway)"}

# ==========================================
# LOGIN (AHORA USA MYSQL)
# ==========================================
@app.post("/login/")
def login(datos_login: LoginSchema, db_sql: Session = Depends(get_db_sql)):
    # 1. Buscamos usuario en la tabla SQL
    usuario_encontrado = db_sql.query(UsuarioSQL).filter(UsuarioSQL.usuario == datos_login.usuario).first()
    
    if not usuario_encontrado:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # 2. Verificamos contraseña
    if usuario_encontrado.contrasena != datos_login.contrasena:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")

    # 3. Retornamos datos y el ID DE MONGO para que el Front siga igual
    return {
        "usuario": usuario_encontrado.usuario,
        "rol": usuario_encontrado.rol,
        "_id": usuario_encontrado.mongo_id 
    }

# Endpoint para crear el primer ADMIN (Ejecutar una vez desde Postman/Docs)
@app.post("/crear-admin-inicial/")
def crear_admin_inicial(usuario: str, contrasena: str, db_sql: Session = Depends(get_db_sql)):
    if db_sql.query(UsuarioSQL).filter(UsuarioSQL.usuario == usuario).first():
        return {"mensaje": "El usuario ya existe"}
    
    admin = UsuarioSQL(
        usuario=usuario,
        contrasena=contrasena,
        rol="jefe",
        mongo_id="admin_sys_id" # ID referencia
    )
    db_sql.add(admin)
    db_sql.commit()
    return {"mensaje": "Admin creado en MySQL correctamente"}

# -----------------------
# CLIENTES (Mongo)
# -----------------------
@app.get("/clientes/")
def listar_clientes():
    return [to_json(c) for c in clientes_col.find()]

@app.post("/clientes/")
def crear_cliente(cliente: dict = Body(...)):
    if clientes_col.find_one({"correo": cliente.get("correo")}):
        raise HTTPException(status_code=400, detail="El cliente ya existe")
    cid = insert_document(clientes_col, cliente)
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
# BARBEROS (HÍBRIDO: SQL + MONGO)
# -----------------------
@app.get("/barberos/")
def listar_barberos():
    # Leemos de Mongo (Perfil público)
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
    if not b:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")
    data = to_json(b)
    data.pop("contrasena", None)
    data["especialidad"] = data.get("especialidad") or "No asignada"
    data["disponibilidades"] = data.get("disponibilidades", [])
    return data

@app.post("/barberos/")
def crear_barbero(barbero: BarberoSchema, db_sql: Session = Depends(get_db_sql)):
    # 1. Validar en MySQL (usuario único)
    existe = db_sql.query(UsuarioSQL).filter(UsuarioSQL.usuario == barbero.usuario).first()
    if existe:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe (SQL)")

    # 2. Insertar Perfil en MongoDB
    hoy = datetime.now().date()
    disponibilidades = [
        {"fecha": (hoy + timedelta(days=i)).isoformat(), "hora": h, "estado": "disponible"}
        for i in range(7) for h in ["08:00","09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00"]
    ]
    
    nuevo_perfil_mongo = {
        "nombre": barbero.nombre,
        "usuario": barbero.usuario,
        "especialidad": barbero.especialidad or "No asignada",
        "disponibilidades": disponibilidades
    }
    
    bid = insert_document(barberos_col, nuevo_perfil_mongo)

    # 3. Insertar Credenciales en MySQL
    nuevo_usuario_sql = UsuarioSQL(
        usuario=barbero.usuario,
        contrasena=barbero.contrasena,
        rol="barbero",
        mongo_id=str(bid) 
    )
    db_sql.add(nuevo_usuario_sql)
    db_sql.commit()

    return {"mensaje": "Barbero creado correctamente en ambas BD", "id": str(bid)}

@app.put("/barberos/{barbero_id}")
def actualizar_barbero(barbero_id: str, data: dict = Body(...)):
    # Actualiza solo perfil en Mongo
    campos = {k: data[k] for k in ["nombre", "especialidad"] if k in data}
    if not campos:
        raise HTTPException(status_code=400, detail="Nada para actualizar")
    modified = update_document(barberos_col, barbero_id, campos)
    if modified == 0:
        raise HTTPException(status_code=404, detail="Barbero no encontrado o sin cambios")
    return {"mensaje": "Perfil actualizado correctamente"}

@app.delete("/barberos/{barbero_id}")
def eliminar_barbero(barbero_id: str, db_sql: Session = Depends(get_db_sql)):
    # 1. Eliminar de Mongo
    deleted = delete_document(barberos_col, barbero_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Barbero no encontrado en Mongo")

    # 2. Eliminar de MySQL (Usando la referencia mongo_id)
    usuario_sql = db_sql.query(UsuarioSQL).filter(UsuarioSQL.mongo_id == barbero_id).first()
    if usuario_sql:
        db_sql.delete(usuario_sql)
        db_sql.commit()

    return {"mensaje": "Barbero eliminado de ambas BD correctamente"}

# Disponibilidades (Mongo)
@app.get("/barberos/{barbero_id}/disponibilidades")
def obtener_disponibilidades(barbero_id: str):
    barbero = barberos_col.find_one({"_id": ObjectId(barbero_id)})
    if not barbero:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")
    return {"barbero_id": barbero_id, "nombre": barbero["nombre"], "disponibilidades": barbero.get("disponibilidades", [])}

@app.put("/disponibilidad/bloquear/{barbero_id}/{fecha}/{hora}")
def bloquear_disponibilidad(barbero_id: str, fecha: str, hora: str):
    r = barberos_col.update_one(
        {"_id": ObjectId(barbero_id), "disponibilidades": {"$elemMatch": {"fecha": fecha, "hora": hora}}},
        {"$set": {"disponibilidades.$.estado": "ocupado"}}
    )
    if r.modified_count == 0:
        raise HTTPException(status_code=404, detail="No se encontró esa hora disponible")
    return {"mensaje": "Horario bloqueado correctamente"}

# -----------------------
# SERVICIOS (Mongo)
# -----------------------
@app.get("/servicios/")
def listar_servicios():
    return [to_json(s) for s in servicios_col.find()]

@app.post("/servicios/")
def crear_servicio(servicio: dict = Body(...)):
    sid = insert_document(servicios_col, servicio)
    return {"mensaje": "Servicio creado correctamente", "id": sid}

@app.put("/servicios/{servicio_id}")
def actualizar_servicio(servicio_id: str, data: dict = Body(...)):
    modified = update_document(servicios_col, servicio_id, data)
    if modified == 0:
        raise HTTPException(status_code=404, detail="Servicio no encontrado o sin cambios")
    return {"mensaje": "Servicio actualizado correctamente"}

@app.delete("/servicios/{servicio_id}")
def eliminar_servicio(servicio_id: str):
    deleted = delete_document(servicios_col, servicio_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return {"mensaje": "Servicio eliminado correctamente"}

# -----------------------
# PRODUCTOS (Mongo)
# -----------------------
@app.get("/productos/")
def listar_productos():
    return [to_json(p) for p in productos_col.find()]

@app.post("/productos/")
def crear_producto(producto: dict = Body(...)):
    pid = insert_document(productos_col, producto)
    return {"mensaje": "Producto creado correctamente", "id": pid}

@app.put("/productos/{producto_id}")
def actualizar_producto(producto_id: str, data: dict = Body(...)):
    modified = update_document(productos_col, producto_id, data)
    if modified == 0:
        raise HTTPException(status_code=404, detail="Producto no encontrado o sin cambios")
    return {"mensaje": "Producto actualizado correctamente"}

@app.delete("/productos/{producto_id}")
def eliminar_producto(producto_id: str):
    deleted = delete_document(productos_col, producto_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"mensaje": "Producto eliminado correctamente"}

# -----------------------
# RESERVAS (Mongo)
# -----------------------
@app.get("/reservas/detalle/")
def listar_reservas_detalle():
    reservas = list(reservas_col.aggregate([
        {"$lookup": {"from": "clientes", "localField": "id_cliente", "foreignField": "_id", "as": "cliente"}},
        {"$lookup": {"from": "servicios", "localField": "id_servicio", "foreignField": "_id", "as": "servicio"}},
        {"$lookup": {"from": "barberos", "localField": "id_barbero", "foreignField": "_id", "as": "barbero"}}
    ]))
    return [to_json(r) for r in reservas]

@app.post("/reservas/")
def crear_reserva(reserva: ReservaCreate):
    try:
        barbero_oid = ObjectId(reserva.id_barbero)
        fecha_str = str(reserva.fecha)
        cliente_oid = None

        if reserva.id_cliente and reserva.id_cliente.strip():
            try:
                cliente_oid = ObjectId(reserva.id_cliente)
            except:
                cliente_oid = None

        if not cliente_oid:
            if not (reserva.nombre_cliente and reserva.email_cliente and reserva.telefono_cliente):
                raise HTTPException(status_code=400, detail="Faltan datos del cliente")
            cliente_doc = {
                "nombre": f"{reserva.nombre_cliente.strip()} {reserva.apellido_cliente.strip() if reserva.apellido_cliente else ''}".strip(),
                "correo": reserva.email_cliente.strip(),
                "telefono": reserva.telefono_cliente.strip(),
                "direccion": None
            }
            existente = clientes_col.find_one({"correo": cliente_doc["correo"]})
            cliente_oid = existente["_id"] if existente else insert_document(clientes_col, cliente_doc)

        servicio_oid = None
        if reserva.id_servicio and reserva.id_servicio.strip():
            try:
                servicio_oid = ObjectId(reserva.id_servicio)
            except:
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

        return {"mensaje": "Reserva creada correctamente", "id_reserva": str(rid)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.put("/reservas/actualizar/{reserva_id}")
def actualizar_reserva(reserva_id: str, data: dict = Body(...)):
    modified = update_document(reservas_col, reserva_id, data)
    if modified == 0:
        raise HTTPException(status_code=404, detail="Reserva no encontrada o sin cambios")
    return {"mensaje": "Reserva actualizada correctamente"}

@app.delete("/reservas/cancelar/{reserva_id}")
def eliminar_reserva(reserva_id: str):
    deleted = delete_document(reservas_col, reserva_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return {"mensaje": "Reserva eliminada correctamente"}

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
        reservas = list(reservas_col.aggregate([
            {"$match": {"id_barbero": oid, "estado": "completado"}},
            {"$lookup": {"from": "clientes", "localField": "id_cliente", "foreignField": "_id", "as": "cliente"}},
            {"$lookup": {"from": "servicios", "localField": "id_servicio", "foreignField": "_id", "as": "servicio"}},
        ]))
        return [to_json(r) for r in reservas]
    except errors.InvalidId:
        raise HTTPException(status_code=400, detail="ID inválido")

# -----------------------
# FUNCIONES AUXILIARES
# -----------------------
def regenerar_disponibilidad():
    try:
        hoy = datetime.now().date()
        futuro = hoy + timedelta(days=7)
        if barberos_col is not None:
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
    except Exception as e:
        print(f"Error regenerando disponibilidad: {e}")

# -----------------------
# RUN SERVER
# -----------------------
if __name__ == "__main__":
    regenerar_disponibilidad()
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)