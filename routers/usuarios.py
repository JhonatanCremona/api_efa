from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from service.useriosService import get_listaUsuarios
from config import db

RouterUsers = APIRouter(prefix="/usuario", tags=["usuarios"])

@RouterUsers.get("/lista-usuarios")
def read_lista_usuarios(skip: int = 0, limit: int = 10, db: Session = Depends(db.get_db)):
    usuario = get_listaUsuarios(db, skip=skip, limit=limit)
    return usuario