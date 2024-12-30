from sqlalchemy.orm import Session
from models.usuario import Usuario

def get_listaUsuarios(db: Session, skip: int = 0, limit: int =10):
    return db.query(Usuario).offset(skip).limit(limit).all()

