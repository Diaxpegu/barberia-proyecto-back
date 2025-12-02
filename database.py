from pymongo import MongoClient
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# ==========================================
# 1. CONFIGURACIÓN MONGODB (Negocio + Login)
# ==========================================
MONGO_URL = os.getenv(
    "MONGO_URL",
    "mongodb://mongo:password@mongodb.railway.internal:27017/test?authSource=admin"
)
MONGO_DB = os.getenv("MONGO_DB", "test")

try:
    client = MongoClient(MONGO_URL)
    db = client[MONGO_DB]
    print("Conexión a MongoDB exitosa")
except Exception as e:
    print("Error al conectar a MongoDB:", e)
    db = None

# Colecciones MongoDB
if db is not None:
    # CLIENTES YA NO ESTÁ AQUÍ (Ahora es MySQL)
    barberos_col = db["barberos"]
    servicios_col = db["servicios"]
    productos_col = db["productos"]
    reservas_col = db["reservas"]
    disponibilidades_col = db["disponibilidades"]
    jefes_col = db["jefes"] # Para login de admin
    # clientes_col se mantiene como variable None o se usa para migración si quisieras
else:
    barberos_col = servicios_col = productos_col = reservas_col = jefes_col = None

# ==========================================
# 2. CONFIGURACIÓN MYSQL (Solo Clientes)
# ==========================================
DB_USER = os.environ.get("MYSQLUSER", "root")
DB_PASS = os.environ.get("MYSQLPASSWORD", "")
DB_HOST = os.environ.get("MYSQLHOST", "mysql.railway.internal")
DB_NAME = os.environ.get("MYSQLDATABASE", "railway")
DB_PORT = os.environ.get("MYSQLPORT", "3306")

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

try:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    print(f" SQL configurado hacia: {DB_HOST}:{DB_PORT}")
except Exception as e:
    print("Error al configurar SQL:", e)
    Base = declarative_base()

# --- Modelo SOLO para Clientes ---
class ClienteSQL(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100))
    correo = Column(String(100), unique=True, index=True)
    telefono = Column(String(20))
    direccion = Column(String(200), nullable=True)
    estado = Column(String(50), default="nuevo") # Para cumplir requisito de actualizar estado

# Crear tablas
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print("No se pudieron crear tablas SQL:", e)

def get_db_sql():
    db_sql = SessionLocal()
    try:
        yield db_sql
    finally:
        db_sql.close()