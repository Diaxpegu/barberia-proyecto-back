from pymongo import MongoClient
import os

# Railway proporciona MONGO_URL automáticamente
MONGO_URL = os.getenv("MONGO_URL")

# Conectar cliente
client = MongoClient(MONGO_URL)
db = client["barberia"]  # nombre de la BD en MongoDB

# Colecciones existentes
clientes_col = db["clientes"]
barberos_col = db["barberos"]
servicios_col = db["servicios"]
productos_col = db["productos"]
reservas_col = db["reservas"]
disponibilidades_col = db["disponibilidades"]
notificaciones_col = db["notificaciones"]
jefes_col = db["jefes"]
