from pymongo import MongoClient
import os

# -----------------------
# Configuración de entorno
# -----------------------
MONGO_URL = os.getenv(
    "MONGO_URL",
    "mongodb://mongo:password@mongodb.railway.internal:27017/test?authSource=admin"
)
MONGO_DB = os.getenv("MONGO_DB", "test")

# -----------------------
# Cliente MongoDB
# -----------------------
try:
    client = MongoClient(MONGO_URL)
    db = client[MONGO_DB]
    print("✅ Conexión a MongoDB exitosa")
except Exception as e:
    print("⚠️ Error al conectar a MongoDB:", e)
    raise e

# -----------------------
# Colecciones
# -----------------------
colecciones = [
    "clientes",
    "barberos",
    "servicios",
    "productos",
    "reservas",
    "disponibilidades",
    "notificaciones",
    "jefes",
    "admin"
]

# Crear variables dinámicas para cada colección
for col_name in colecciones:
    globals()[f"{col_name}_col"] = db[col_name]

print("📂 Colecciones disponibles:", ", ".join(colecciones))



