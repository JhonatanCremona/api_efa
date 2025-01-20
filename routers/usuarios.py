from fastapi import APIRouter, HTTPException, Depends, status
from datetime import timedelta, datetime, timezone
from sqlalchemy.orm import Session
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from service.useriosService import get_listaUsuarios
from config import db
from typing import Annotated
from models import usuario
from dotenv import load_dotenv
from jose import jwt, JWTError
import os
from desp import db_dependency, bcrypt_context

load_dotenv()

RouterUsers = APIRouter(prefix="/usuario", tags=["usuarios"])
SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
ALGORITHM = os.getenv("AUTH_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class UserCreateRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

def authenticate_user(username: str, password: str, db):
    user = db.query(usuario).filter(usuario.name == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.password):
        return False
    return user

def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

@RouterUsers.get("/lista-usuarios")
def read_lista_usuarios(skip: int = 0, limit: int = 10, db: Session = Depends(db.get_db)):
    usuario = get_listaUsuarios(db, skip=skip, limit=limit)
    return usuario

@RouterUsers.post("/login", response_model= Token)
async def loginAccesoToken(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user.username, user.id , expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}