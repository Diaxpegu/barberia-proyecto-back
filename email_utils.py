import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def enviar_correo_recordatorio(destinatario, nombre_cliente, fecha, hora, servicio):
    sender_email = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")
    smtp_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("MAIL_PORT", 587))

    # Validar configuración SMTP
    if not sender_email or not password:
        print("⚠️ Error: MAIL_USERNAME o MAIL_PASSWORD no están configurados.")
        return False

    subject = "⏰ Recordatorio de tu cita en Valiant Barbería"
    body = f"""
    Hola {nombre_cliente},

    Te recordamos que tienes una cita mañana:

    📅 Fecha: {fecha}
    🕒 Hora: {hora}
    ✂️ Servicio: {servicio}

    ¡Te esperamos!
    """

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = destinatario
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)

        return True

    except Exception as e:
        print("⚠️ Error enviando correo:", e)
        return False
