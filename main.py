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

app = FastAPI(title="API Barbería", version="2.1.0")

# CORS (Permisivo para evitar errores)
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
# MODELOS DE DATOS
# -----------------------
class LoginSchema(BaseModel):
    usuario: str
    contrasena: str

class ClienteSchema(BaseModel):
    nombre: str
    correo: str
    telefono: str
    direccion: Optional[str] = None

class ReservaCreate(BaseModel):
    id_barbero: str
    fecha: str
    hora: str
    id_cliente: Optional[str] = None # ID de MySQL si ya existe
    id_servicio: Optional[str] = None
    # Datos para crear cliente al vuelo si no existe
    nombre_cliente: Optional[str] = None
    apellido_cliente: Optional[str] = None
    email_cliente: Optional[str] = None
    telefono_cliente: Optional[str] = None
    servicio_nombre: Optional[str] = None

@app.get("/")
def root():
    return {"mensaje": "API Funcionando: Clientes en MySQL, resto en MongoDB"}

# ==========================================
# LOGIN (VUELVE A MONGODB)
# ==========================================
@app.post("/login/")
def login(datos_login: LoginSchema):
    usuario, contrasena = datos_login.usuario, datos_login.contrasena
    
    # 1. Buscar en Barberos (Mongo)
    barbero = barberos_col.find_one({"usuario": usuario})
    if barbero and barbero.get("contrasena") == contrasena:
        return {"usuario": barbero["usuario"], "rol": "barbero", "_id": str(barbero["_id"])}
    
    # 2. Buscar en Jefes (Mongo)
    # Nota: Asegúrate de tener jefes en tu colección de mongo 'jefes'
    jefe = jefes_col.find_one({"usuario": usuario})
    if jefe and jefe.get("contrasena") == contrasena:
        return {"usuario": jefe["usuario"], "rol": "jefe", "_id": str(jefe["_id"])}

    raise HTTPException(status_code=404, detail="Usuario o contraseña incorrectos")

# ==========================================
# CLIENTES (AHORA EN MYSQL)
# ==========================================
@app.get("/clientes/")
def listar_clientes(db_sql: Session = Depends(get_db_sql)):
    clientes = db_sql.query(ClienteSQL).all()
    return clientes

@app.post("/clientes/")
def crear_cliente(cliente: ClienteSchema, db_sql: Session = Depends(get_db_sql)):
    # Verificar existencia
    existe = db_sql.query(ClienteSQL).filter(ClienteSQL.correo == cliente.correo).first()
    if existe:
        raise HTTPException(status_code=400, detail="El cliente ya existe (correo duplicado)")
    
    nuevo_cliente = ClienteSQL(
        nombre=cliente.nombre,
        correo=cliente.correo,
        telefono=cliente.telefono,
        direccion=cliente.direccion,
        estado="registrado"
    )
    db_sql.add(nuevo_cliente)
    db_sql.commit()
    db_sql.refresh(nuevo_cliente)
    return {"mensaje": "Cliente creado en MySQL", "id": new_cliente.id}

# ==========================================
# RESERVAS (MONGODB + MYSQL LINK)
# ==========================================
@app.post("/reservas/")
def crear_reserva(reserva: ReservaCreate, db_sql: Session = Depends(get_db_sql)):
    try:
        # 1. GESTIÓN DEL CLIENTE (MYSQL)
        mysql_client_id = None
        
        # Datos del cliente que vienen del formulario
        correo = reserva.email_cliente.strip() if reserva.email_cliente else None
        
        if correo:
            # Buscamos si ya existe en MySQL
            cliente_sql = db_sql.query(ClienteSQL).filter(ClienteSQL.correo == correo).first()
            
            if cliente_sql:
                mysql_client_id = cliente_sql.id
                # Opcional: Actualizar datos si cambiaron
            else:
                # CREAR CLIENTE EN MYSQL
                nombre_completo = f"{reserva.nombre_cliente} {reserva.apellido_cliente or ''}".strip()
                nuevo_cliente = ClienteSQL(
                    nombre=nombre_completo,
                    correo=correo,
                    telefono=reserva.telefono_cliente,
                    estado="con_reserva"
                )
                db_sql.add(nuevo_cliente)
                db_sql.commit()
                db_sql.refresh(nuevo_cliente)
                mysql_client_id = nuevo_cliente.id
        else:
            raise HTTPException(status_code=400, detail="Se requiere email del cliente")

        # 2. GESTIÓN DE LA RESERVA (MONGODB)
        barbero_oid = ObjectId(reserva.id_barbero)
        fecha_str = str(reserva.fecha)
        
        # Buscamos servicio ID si viene nombre
        servicio_oid = None
        if reserva.id_servicio:
             try: servicio_oid = ObjectId(reserva.id_servicio)
             except: pass
        
        doc_reserva = {
            "id_barbero": barbero_oid,
            "id_cliente_mysql": mysql_client_id, # Guardamos el ID Entero de MySQL
            "id_servicio": servicio_oid,
            "servicio_nombre": reserva.servicio_nombre,
            "fecha": fecha_str,
            "hora": reserva.hora,
            "estado": "pendiente",
            # Guardamos copia de datos cliente por si acaso (desnormalización)
            "datos_cliente_snapshot": { 
                "nombre": f"{reserva.nombre_cliente} {reserva.apellido_cliente or ''}",
                "correo": correo
            }
        }
        rid = insert_document(reservas_col, doc_reserva)

        # 3. ACTUALIZAR DISPONIBILIDAD BARBERO (MONGO)
        barberos_col.update_one(
            {"_id": barbero_oid, "disponibilidades": {"$elemMatch": {"fecha": fecha_str, "hora": reserva.hora}}},
            {"$set": {"disponibilidades.$.estado": "pendiente"}}
        )

        return {"mensaje": "Reserva creada (Cliente en SQL, Reserva en Mongo)", "id_reserva": str(rid)}

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/reservas/detalle/")
def listar_reservas_detalle(db_sql: Session = Depends(get_db_sql)):
    # Obtenemos reservas de Mongo
    reservas_mongo = list(reservas_col.find())
    resultado = []
    
    for r in reservas_mongo:
        r_json = to_json(r)
        
        # MANUAL JOIN: Buscar datos del cliente en MySQL usando el ID guardado
        if "id_cliente_mysql" in r and r["id_cliente_mysql"]:
            cliente_sql = db_sql.query(ClienteSQL).filter(ClienteSQL.id == r["id_cliente_mysql"]).first()
            if cliente_sql:
                r_json["cliente"] = [{
                    "nombre": cliente_sql.nombre,
                    "correo": cliente_sql.correo,
                    "telefono": cliente_sql.telefono,
                    "estado_cliente": cliente_sql.estado
                }]
            else:
                 r_json["cliente"] = [{"nombre": "Cliente Eliminado de SQL"}]
        
        # Lookup manual sencillo para barbero (si es necesario)
        if "id_barbero" in r:
             try:
                b = barberos_col.find_one({"_id": ObjectId(r["id_barbero"])})
                if b: r_json["barbero"] = [{"nombre": b.get("nombre")}]
             except: pass

        resultado.append(r_json)
        
    return resultado

@app.put("/reservas/actualizar/{reserva_id}")
def actualizar_reserva(reserva_id: str, data: dict = Body(...), db_sql: Session = Depends(get_db_sql)):
    # 1. Actualizar en Mongo
    modified = update_document(reservas_col, reserva_id, data)
    
    # 2. "CASCADA": Si el estado cambia a 'realizado', actualizar cliente en MySQL
    if "estado" in data:
        nuevo_estado = data["estado"]
        # Buscamos la reserva para saber qué cliente es
        reserva = reservas_col.find_one({"_id": ObjectId(reserva_id)})
        
        if reserva and "id_cliente_mysql" in reserva:
            cliente_id = reserva["id_cliente_mysql"]
            cliente_sql = db_sql.query(ClienteSQL).filter(ClienteSQL.id == cliente_id).first()
            
            if cliente_sql:
                # Actualizamos el estado del cliente en MySQL
                if nuevo_estado == "completado" or nuevo_estado == "realizado":
                    cliente_sql.estado = "atendido"
                elif nuevo_estado == "cancelado":
                    cliente_sql.estado = "reservas_canceladas"
                
                db_sql.commit()

    return {"mensaje": "Reserva y estado de cliente actualizados"}

# ==========================================
# BARBEROS (MONGO)
# ==========================================
@app.get("/barberos/")
def listar_barberos():
    lista = []
    for b in barberos_col.find():
        data = to_json(b)
        data.pop("contrasena", None)
        lista.append(data)
    return lista

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

# Endpoint auxiliar para crear JEFE en Mongo (Ya que el login busca ahi)
@app.post("/crear-jefe-mongo/")
def crear_jefe(usuario: str, contrasena: str):
    if jefes_col.find_one({"usuario": usuario}):
        return {"mensaje": "Jefe ya existe"}
    jefes_col.insert_one({"usuario": usuario, "contrasena": contrasena})
    return {"mensaje": "Jefe creado en Mongo"}

# ==========================================
# RESTO DE ENDPOINTS (SERVICIOS, ETC) - MANTIENEN IGUAL
# ==========================================
@app.get("/servicios/")
def listar_servicios():
    return [to_json(s) for s in servicios_col.find()]

@app.get("/barbero/agenda/{barbero_id}")
def get_agenda(barbero_id: str):
    # Simplificado para brevedad, misma lógica que antes pero sin lookup complejo automático
    # ya que clientes están en SQL.
    # El front de barbero podría necesitar ajuste si usa muchos datos del cliente, 
    # pero para ver fecha/hora funcionará con los datos snapshot o IDs.
    try:
        oid = ObjectId(barbero_id)
        reservas = list(reservas_col.find({"id_barbero": oid}))
        return [to_json(r) for r in reservas]
    except:
        return []

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)