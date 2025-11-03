from pymongo import MongoClient
import os

# -----------------------
# Configuración de entorno
# -----------------------
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://mongo:password@mongodb.railway.internal:27017/test?authSource=admin"
    
)
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://ignacio_user:1234@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority")
MONGO_DB = os.getenv("MONGO_DB", "barberia")  # Nombre de la base de datos

# -----------------------
# Cliente MongoDB
# -----------------------
try:
    client = MongoClient(MONGO_URI)
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

"""from pymongo import MongoClient
import os

# Variables de entorno de Railway
MONGO_USER = os.getenv("MONGOUSER", "mongo")
MONGO_PASS = os.getenv("MONGOPASSWORD", "")
MONGO_HOST = os.getenv("MONGOHOST", "mongodb.railway.internal")
MONGO_PORT = os.getenv("MONGOPORT", "27017")
MONGO_DB = "test"  # Nombre de tu base de datos

# Construir URL de conexión (si no se define directamente en Railway)
MONGO_URL = os.getenv("MONGO_URL") or f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin"
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
jefes_col = db["jefes"]"""
