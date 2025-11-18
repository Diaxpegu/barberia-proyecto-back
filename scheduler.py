from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from database import reservas_col, clientes_col
from email_utils import enviar_correo_recordatorio

scheduler = BackgroundScheduler()


def chequear_reservas_proximas():
    print("🔄 Revisando reservas para enviar recordatorios...")

    mañana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    reservas = reservas_col.find({
        "fecha": mañana,
        "estado": {"$in": ["pendiente", "confirmado"]},
        "notificacion_enviada": {"$ne": True}
    })

    enviados = 0

    for reserva in reservas:
        cliente = clientes_col.find_one({"_id": reserva["id_cliente"]})
        if not cliente:
            continue
        
        enviado = enviar_correo_recordatorio(
            destinatario=cliente["correo"],
            nombre_cliente=cliente.get("nombre", "Cliente"),
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

    print(f"📨 Recordatorios enviados: {enviados}")


def iniciar_scheduler():
    if not scheduler.running:
        scheduler.add_job(chequear_reservas_proximas, "interval", minutes=60)
        scheduler.start()
        print("🚀 Scheduler de recordatorios iniciado.")
