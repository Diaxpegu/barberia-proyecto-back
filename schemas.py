from pydantic import BaseModel, EmailStr

#Base común para Cliente (entrada y salida)
class ClienteBase(BaseModel):
    nombre: str
    correo: EmailStr  # valida automáticamente que sea un email válido


class ClienteCreate(ClienteBase):
    pass  # hereda nombre y correo de ClienteBase


class ClienteOut(ClienteBase):
    id: int  # agregamos id para que se vea en la respuesta

    class Config:
        orm_mode = True  # permite convertir objetos SQLAlchemy a JSON
