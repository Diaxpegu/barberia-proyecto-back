from sqlalchemy.orm import Session
import models as models, schemas as schemas

def get_clientes(db: Session):
    return db.query(models.Cliente).all()

def get_cliente(db: Session, cliente_id: int):
    return db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()

def create_cliente(db: Session, cliente: schemas.ClienteCreate):
    db_cliente = models.Cliente(nombre=cliente.nombre, correo=cliente.correo)
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente
