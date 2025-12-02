from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
# CORRECCIÓN: Importamos SessionLocal y ClienteSQL en lugar de clientes_col
from database import reservas_col, SessionLocal, ClienteSQL
from email_utils import enviar_correo_recordatorio

scheduler = BackgroundScheduler()

def chequear_reservas_proximas():
    print(" Revisando reservas para enviar recordatorios...")

    mañana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Buscamos reservas pendientes para mañana en Mongo
    reservas = reservas_col.find({
        "fecha": mañana,
        "estado": {"$in": ["pendiente", "confirmado"]},
        "notificacion_enviada": {"$ne": True}
    })

    enviados = 0
    
    # Abrimos conexión a MySQL para consultar los correos
    db_sql = SessionLocal()

    try:
        for reserva in reservas:
            email_destino = None
            nombre_destino = "Cliente"

            # 1. Intentar obtener datos de MySQL
            if "id_cliente_mysql" in reserva and reserva["id_cliente_mysql"]:
                cliente_sql = db_sql.query(ClienteSQL).filter(ClienteSQL.id == reserva["id_cliente_mysql"]).first()
                if cliente_sql:
                    email_destino = cliente_sql.correo
                    nombre_destino = cliente_sql.nombre
            
            # 2. Respaldo: Usar el snapshot guardado en Mongo (si existe)
            if not email_destino and "datos_cliente_snapshot" in reserva:
                email_destino = reserva["datos_cliente_snapshot"].get("correo")
                nombre_destino = reserva["datos_cliente_snapshot"].get("nombre")

            # Si encontramos un email, enviamos el correo
            if email_destino:
                enviado = enviar_correo_recordatorio(
                    destinatario=email_destino,
                    nombre_cliente=nombre_destino,
                    fecha=reserva["fecha"],
                    hora=reserva["hora"],
                    servicio=reserva.get("servicio_nombre", "Servicio de barbería")
                )

                if enviado:
                    reservas_col.update_one(
                        {"_id": reserva["_id"]},
                        {"$set": {"notificacion_enviada": True}}
                    )
                    enviados += 1
                    
    except Exception as e:
        print(f" Error en scheduler: {e}")
    finally:
        # Cerramos la conexión SQL pase lo que pase
        db_sql.close()

    print(f" Recordatorios enviados: {enviados}")


def iniciar_scheduler():
    if not scheduler.running:
        scheduler.add_job(chequear_reservas_proximas, "interval", minutes=60)
        scheduler.start()
        print(" Scheduler de recordatorios iniciado (Modo Híbrido).")