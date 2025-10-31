from pymongo import MongoClient
import os

# URL de conexión que Railway proporciona como variable MONGO_URL
MONGO_URL = os.getenv("MONGO_URL")

# Conectar cliente
client = MongoClient(MONGO_URL)

# Nombre de la base de datos (en tu caso es "test")
db = client["test"]

# Colecciones existentes
clientes_col = db["clientes"]
barberos_col = db["barberos"]
servicios_col = db["servicios"]
productos_col = db["productos"]
reservas_col = db["reservas"]
disponibilidades_col = db["disponibilidades"]
notificaciones_col = db["notificaciones"]
jefes_col = db["jefes"]
