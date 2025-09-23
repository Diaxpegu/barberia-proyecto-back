from flask import Flask, render_template, url_for
from app.models import get_peluqueros

app = Flask(__name__)

@app.route("/")
def index():
    peluqueros = get_peluqueros()
    return render_template("peluqueros.html", peluqueros=peluqueros)

@app.route("/reserva/<int:peluquero_id>")
def reserva(peluquero_id):
    return f"Reservar cita con peluquero {peluquero_id}"

@app.route("/panel/<int:peluquero_id>")
def panel_peluquero(peluquero_id):
    return f"Panel del peluquero {peluquero_id}"
