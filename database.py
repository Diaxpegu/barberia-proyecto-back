import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_USER = os.environ.get("MYSQLUSER", "root")
DB_PASS = os.environ.get("MYSQLPASSWORD", "")
DB_HOST = os.environ.get("MYSQLHOST", "mysql.railway.internal")
DB_NAME = os.environ.get("MYSQLDATABASE", "railway")
DB_PORT = int(os.environ.get("MYSQLPORT", 3306))

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
