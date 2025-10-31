from pymongo import MongoClient
import os

# Variables de entorno de Railway
MONGO_USER = os.getenv("MONGOUSER", "mongo")
MONGO_PASS = os.getenv("MONGOPASSWORD", "")
MONGO_HOST = os.getenv("MONGOHOST", "mongodb.railway.internal")
MONGO_PORT = os.getenv("MONGOPORT", "27017")
MONGO_DB = "test"  # Nombre de tu base de datos

# Construir URL de conexión (si no se define directamente en Railway)
MONGO_URL = os.getenv("MONGO_URL") or f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}"

# Crear cliente y conectar base de datos
client = MongoClient(MONGO_URL)
db = client[MONGO_DB]

# Colecciones existentes
clientes_col = db["clientes"]
barberos_col = db["barberos"]
servicios_col = db["servicios"]
productos_col = db["productos"]
reservas_col = db["reservas"]
disponibilidades_col = db["disponibilidades"]
notificaciones_col = db["notificaciones"]
jefes_col = db["jefes"]
