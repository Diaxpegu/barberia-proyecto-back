import os
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import Cliente

# Crear tablas bd
Base.metadata.create_all(bind=engine)

app = FastAPI()

class ClienteSchema(BaseModel):
    nombre: str
    correo: str

@app.post("/clientes/")
def crear_cliente(cliente: ClienteSchema):
    db: Session = SessionLocal()
    nuevo = Cliente(nombre=cliente.nombre, correo=cliente.correo)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    db.close()
    return {"id": nuevo.id, "nombre": nuevo.nombre, "correo": nuevo.correo}

# Conexion para railway
if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
