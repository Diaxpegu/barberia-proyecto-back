from pymongo import MongoClient
import os

# -----------------------
# Configuración de entorno
# -----------------------
MONGO_URL = os.getenv(
    "MONGO_URL",
    "mongodb://mongo:password@mongodb.railway.internal:27017/test?authSource=admin"
    
)
MONGO_DB = os.getenv("MONGO_DB", "test")  # Nombre de la base de datos

# -----------------------
# Cliente MongoDB
# -----------------------
try:
    client = MongoClient(MONGO_URL)
    db = client[MONGO_DB]
    print("Conexión a MongoDB exitosa")
except Exception as e:
    print("Error al conectar a MongoDB:", e)
    raise e

# -----------------------
# Colecciones
# -----------------------
clientes_col = db["clientes"]
barberos_col = db["barberos"]
servicios_col = db["servicios"]
productos_col = db["productos"]
reservas_col = db["reservas"]
disponibilidades_col = db["disponibilidades"]
notificaciones_col = db["notificaciones"]
jefes_col = db["jefes"]
admin_col = db["admin"]



