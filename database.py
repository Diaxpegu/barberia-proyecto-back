from pymongo import MongoClient
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# ==========================================
# CONFIGURACIÓN MONGODB (NoSQL)
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
    clientes_col = db["clientes"]
    barberos_col = db["barberos"]
    servicios_col = db["servicios"]
    productos_col = db["productos"]
    reservas_col = db["reservas"]
    disponibilidades_col = db["disponibilidades"]
    notificaciones_col = db["notificaciones"]
else:
    clientes_col = barberos_col = servicios_col = productos_col = reservas_col = None


# ==========================================
# CONFIGURACIÓN MYSQL (SQL)
# ==========================================

# Railway proporciona estas variables por defecto.
DB_USER = os.environ.get("MYSQLUSER", "root")
DB_PASS = os.environ.get("MYSQLPASSWORD", "")
DB_HOST = os.environ.get("MYSQLHOST", "mysql.railway.internal")
DB_NAME = os.environ.get("MYSQLDATABASE", "railway")
DB_PORT = os.environ.get("MYSQLPORT", "3306")

# Construcción manual de la URL
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

try:
    # pool_pre_ping=True ayuda a reconectar si la conexión se cae
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    print(f"SQL configurado hacia: {DB_HOST}:{DB_PORT}")
except Exception as e:
    print("Error al configurar SQL:", e)
    Base = declarative_base()

# --- Modelo de Tabla Usuarios (SQL) ---
class UsuarioSQL(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String(50), unique=True, index=True)  # Login
    contrasena = Column(String(100))                       # Password
    rol = Column(String(20))                               # 'jefe' o 'barbero'
    mongo_id = Column(String(50))                          # ID vinculado de Mongo

# --- NUEVO: Modelo de Tabla Clientes (SQL) ---
class ClienteSQL(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100))
    apellido = Column(String(100), nullable=True)
    correo = Column(String(100), unique=True, index=True)
    telefono = Column(String(50))
    rut = Column(String(20), nullable=True)
    estado = Column(String(20), default="nuevo")

# Crear tablas automáticamente al iniciar
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print("No se pudieron crear tablas SQL:", e)

# Dependencia para usar la DB en los endpoints
def get_db_sql():
    db_sql = SessionLocal()
    try:
        yield db_sql
    finally:
        db_sql.close()