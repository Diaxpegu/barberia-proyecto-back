from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
# Importamos SessionLocal y ClienteSQL para acceder a MySQL
from database import reservas_col, SessionLocal, ClienteSQL
from email_utils import enviar_correo_recordatorio

scheduler = BackgroundScheduler()

def chequear_reservas_proximas():
    mañana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    reservas = reservas_col.find({
        "fecha": mañana,
        "estado": {"$in": ["pendiente", "confirmado"]},
        "notificacion_enviada": {"$ne": True}
    })

    db_sql = SessionLocal() # Abrir sesión SQL
    try:
        for reserva in reservas: 
            email = None
            nombre = "Cliente"


            # 1. Buscar en MySQL
            if "id_cliente_mysql" in reserva and reserva["id_cliente_mysql"]:
                c = db_sql.query(ClienteSQL).filter(ClienteSQL.id == reserva["id_cliente_mysql"]).first()
                if c:
                    email = c.correo
                    nombre = c.nombre
            
            # 2. Fallback Snapshot
            if not email and "datos_cliente_snapshot" in reserva:
                snap = reserva["datos_cliente_snapshot"]
                email = snap.get("correo")
                nombre = snap.get("nombre")

            if email:
                enviado = enviar_correo_recordatorio(email, nombre, reserva["fecha"], reserva["hora"], reserva.get("servicio_nombre"))
                if enviado:
                    reservas_col.update_one({"_id": reserva["_id"]}, {"$set": {"notificacion_enviada": True}})
    except Exception as e:
        print(f"Error scheduler: {e}")
    finally:
        db_sql.close()

def iniciar_scheduler():
    if not scheduler.running:
        scheduler.add_job(chequear_reservas_proximas, "interval", minutes=60)
        scheduler.start()